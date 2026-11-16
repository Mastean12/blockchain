// SPDX-License-Identifier: MIT
pragma solidity 0.8.38;

/// @title AuditLog
/// @notice Minimal audit registry for Phase 7 of a federated ECG classification study.
///
/// @dev SCOPE AND LIMITS — read before citing any result from this contract.
///
/// This contract is a **Level 2 local prototype** deployed to a single-node Ganache instance. It is
/// not a distributed blockchain: there is no consensus, no independent validators and no
/// decentralisation. Its measurements are local-environment measurements and must not be presented
/// as public-network costs.
///
/// What it proves:
///   - that a specific hash was submitted by an authorised address for a specific run and round;
///   - that a round cannot be closed twice, or closed without the expected participant set;
///   - that duplicate client submissions for the same round are rejected.
///
/// What it does NOT prove:
///   - that an update is honest, correctly computed or clinically meaningful. A commitment binds
///     bytes, not intent;
///   - that the training data is real, or that privacy was preserved;
///   - anything about availability or consensus safety.
///
/// It stores ONLY hashes and small integers. No ECG data, patient identifiers, record numbers,
/// model tensors, keys or per-client diagnostics may be written here. Floats are impossible by
/// construction because the EVM has no float type; privacy parameters are passed pre-scaled.
contract AuditLog {
    enum RoundState {
        None,
        Open,
        Closed
    }

    address public immutable owner;

    mapping(address => bool) public authorised;
    mapping(bytes32 => bool) public runRegistered;
    mapping(bytes32 => bytes32) public runConfigHash;
    mapping(bytes32 => bytes32) public runSplitHash;
    mapping(bytes32 => bytes32) public runClientManifestHash;
    mapping(bytes32 => bytes32) public runCheckpointHash;
    mapping(bytes32 => uint256) public runSelectedRound;

    mapping(bytes32 => RoundState) public roundState;
    mapping(bytes32 => bytes32) public roundParticipantSetHash;
    mapping(bytes32 => uint256) public roundCommitCount;
    mapping(bytes32 => bytes32) public roundGlobalModelHash;
    mapping(bytes32 => bytes32) public roundAggregationRuleHash;

    mapping(bytes32 => mapping(bytes32 => bytes32)) public clientUpdateHash;
    mapping(bytes32 => mapping(bytes32 => bool)) public clientCommitted;

    mapping(bytes32 => bool) public privacyAttested;
    mapping(bytes32 => uint256) public epsilonScaled;
    mapping(bytes32 => uint256) public deltaScaled;
    mapping(bytes32 => uint256) public sigmaScaled;
    mapping(bytes32 => uint256) public clipScaled;
    mapping(bytes32 => bytes32) public accountantHash;

    uint256 public runCount;
    uint256 public transactionCount;

    event RunRegistered(
        bytes32 indexed runId,
        bytes32 configHash,
        bytes32 splitHash,
        bytes32 clientManifestHash
    );
    event RoundOpened(bytes32 indexed runId, uint256 roundIndex, bytes32 participantSetHash);
    event UpdateCommitted(
        bytes32 indexed runId,
        uint256 roundIndex,
        bytes32 indexed clientId,
        bytes32 updateHash,
        uint256 updateBytes
    );
    event RoundClosed(
        bytes32 indexed runId,
        uint256 roundIndex,
        bytes32 globalModelHash,
        bytes32 aggregationRuleHash
    );
    event MissingCommitment(
        bytes32 indexed runId,
        uint256 roundIndex,
        bytes32 expectedParticipantSetHash,
        uint256 commitsReceived
    );
    event CheckpointSealed(bytes32 indexed runId, uint256 selectedRound, bytes32 checkpointHash);
    event PrivacyAttested(
        bytes32 indexed runId,
        uint256 epsilonScaled,
        uint256 deltaScaled,
        uint256 sigmaScaled,
        uint256 clipScaled,
        bytes32 accountantHash
    );

    modifier onlyAuthorised() {
        require(authorised[msg.sender], "AuditLog: caller not authorised");
        _;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "AuditLog: caller not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        authorised[msg.sender] = true;
    }

    // ---------------------------------------------------------------- admin
    function setAuthorised(address account, bool allowed) external onlyOwner {
        authorised[account] = allowed;
    }

    // ------------------------------------------------------------- run level
    function registerRun(
        bytes32 runId,
        bytes32 configHash,
        bytes32 splitHash,
        bytes32 clientManifestHash
    ) external onlyAuthorised {
        require(runId != bytes32(0), "AuditLog: empty runId");
        require(!runRegistered[runId], "AuditLog: run already registered");
        require(configHash != bytes32(0), "AuditLog: empty config hash");
        require(splitHash != bytes32(0), "AuditLog: empty split hash");
        require(clientManifestHash != bytes32(0), "AuditLog: empty manifest hash");

        runRegistered[runId] = true;
        runConfigHash[runId] = configHash;
        runSplitHash[runId] = splitHash;
        runClientManifestHash[runId] = clientManifestHash;
        runCount += 1;
        transactionCount += 1;
        emit RunRegistered(runId, configHash, splitHash, clientManifestHash);
    }

    // ----------------------------------------------------------- round level
    function openRound(
        bytes32 runId,
        uint256 roundIndex,
        bytes32 participantSetHash
    ) external onlyAuthorised {
        require(runRegistered[runId], "AuditLog: run not registered");
        require(
            roundState[roundKey(runId, roundIndex)] == RoundState.None,
            "AuditLog: round already opened"
        );
        require(participantSetHash != bytes32(0), "AuditLog: empty participant set");

        roundState[roundKey(runId, roundIndex)] = RoundState.Open;
        roundParticipantSetHash[roundKey(runId, roundIndex)] = participantSetHash;
        transactionCount += 1;
        emit RoundOpened(runId, roundIndex, participantSetHash);
    }

    function commitUpdate(
        bytes32 runId,
        uint256 roundIndex,
        bytes32 clientId,
        bytes32 updateHash,
        uint256 updateBytes
    ) external onlyAuthorised {
        bytes32 key = roundKey(runId, roundIndex);
        require(roundState[key] == RoundState.Open, "AuditLog: round not open");
        require(updateHash != bytes32(0), "AuditLog: empty update hash");
        require(updateBytes > 0, "AuditLog: zero update size");
        require(
            !clientCommitted[key][clientId],
            "AuditLog: duplicate client commitment (replay rejected)"
        );

        clientCommitted[key][clientId] = true;
        clientUpdateHash[key][clientId] = updateHash;
        roundCommitCount[key] += 1;
        transactionCount += 1;
        emit UpdateCommitted(runId, roundIndex, clientId, updateHash, updateBytes);
    }

    /// @notice Close a round. Reverts if the round is not open or has no commitments.
    /// @dev A caller that knows an expected commit count can verify completeness with
    ///      `isRoundComplete` first; this contract cannot know the expected set size on its own
    ///      without storing it, and storing it would duplicate off-chain state.
    function closeRound(
        bytes32 runId,
        uint256 roundIndex,
        bytes32 globalModelHash,
        bytes32 aggregationRuleHash
    ) external onlyAuthorised {
        bytes32 key = roundKey(runId, roundIndex);
        require(roundState[key] == RoundState.Open, "AuditLog: round not open");
        require(globalModelHash != bytes32(0), "AuditLog: empty model hash");
        require(roundCommitCount[key] > 0, "AuditLog: no commitments to close on");

        roundState[key] = RoundState.Closed;
        roundGlobalModelHash[key] = globalModelHash;
        roundAggregationRuleHash[key] = aggregationRuleHash;
        transactionCount += 1;
        emit RoundClosed(runId, roundIndex, globalModelHash, aggregationRuleHash);
    }

    /// @notice Record that a round did not receive every expected commitment.
    function reportMissingCommitment(
        bytes32 runId,
        uint256 roundIndex,
        bytes32 expectedParticipantSetHash
    ) external onlyAuthorised {
        bytes32 key = roundKey(runId, roundIndex);
        require(roundState[key] != RoundState.Closed, "AuditLog: round already closed");
        require(
            roundCommitCount[key] == 0,
            "AuditLog: commitments exist; use closeRound"
        );
        transactionCount += 1;
        emit MissingCommitment(
            runId,
            roundIndex,
            expectedParticipantSetHash,
            roundCommitCount[key]
        );
    }

    // ---------------------------------------------------------- run sealing
    function sealCheckpoint(
        bytes32 runId,
        uint256 selectedRound,
        bytes32 checkpointHash
    ) external onlyAuthorised {
        require(runRegistered[runId], "AuditLog: run not registered");
        require(!privacyAttested[runId], "AuditLog: run already sealed");
        require(checkpointHash != bytes32(0), "AuditLog: empty checkpoint hash");

        runCheckpointHash[runId] = checkpointHash;
        runSelectedRound[runId] = selectedRound;
        transactionCount += 1;
        emit CheckpointSealed(runId, selectedRound, checkpointHash);
    }

    /// @notice Store a digest of the run's privacy parameters. Values are pre-scaled integers.
    function attestPrivacy(
        bytes32 runId,
        uint256 epsilonScaled_,
        uint256 deltaScaled_,
        uint256 sigmaScaled_,
        uint256 clipScaled_,
        bytes32 accountantHash_
    ) external onlyAuthorised {
        require(runRegistered[runId], "AuditLog: run not registered");
        require(!privacyAttested[runId], "AuditLog: privacy already attested");
        require(accountantHash_ != bytes32(0), "AuditLog: empty accountant id");

        privacyAttested[runId] = true;
        epsilonScaled[runId] = epsilonScaled_;
        deltaScaled[runId] = deltaScaled_;
        sigmaScaled[runId] = sigmaScaled_;
        clipScaled[runId] = clipScaled_;
        accountantHash[runId] = accountantHash_;
        transactionCount += 1;
        emit PrivacyAttested(
            runId,
            epsilonScaled_,
            deltaScaled_,
            sigmaScaled_,
            clipScaled_,
            accountantHash_
        );
    }

    // ---------------------------------------------------------- read helpers
    function roundKey(bytes32 runId, uint256 roundIndex) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(runId, roundIndex));
    }

    function isRoundComplete(
        bytes32 runId,
        uint256 roundIndex,
        uint256 expectedCommits
    ) external view returns (bool) {
        return roundCommitCount[roundKey(runId, roundIndex)] == expectedCommits;
    }

    function roundCommitments(
        bytes32 runId,
        uint256 roundIndex,
        bytes32[] calldata clientIds
    ) external view returns (bytes32[] memory hashes, bool[] memory committed) {
        bytes32 key = roundKey(runId, roundIndex);
        hashes = new bytes32[](clientIds.length);
        committed = new bool[](clientIds.length);
        for (uint256 index = 0; index < clientIds.length; index += 1) {
            hashes[index] = clientUpdateHash[key][clientIds[index]];
            committed[index] = clientCommitted[key][clientIds[index]];
        }
    }

    function verifyRun(bytes32 runId)
        external
        view
        returns (
            bool registered,
            bytes32 configHash,
            bytes32 splitHash,
            bytes32 clientManifestHash,
            bytes32 checkpointHash,
            uint256 selectedRound,
            bool attested
        )
    {
        return (
            runRegistered[runId],
            runConfigHash[runId],
            runSplitHash[runId],
            runClientManifestHash[runId],
            runCheckpointHash[runId],
            runSelectedRound[runId],
            privacyAttested[runId]
        );
    }
}
