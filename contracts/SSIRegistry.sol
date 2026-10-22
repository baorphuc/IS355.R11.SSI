// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import {IdentitySBT} from "./IdentitySBT.sol";

contract SSIRegistry is AccessControl {
    using MessageHashUtils for bytes32;

    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");

    enum CredentialStatus { NONE, REQUESTED, ISSUED, REVOKED }

    struct Identity {
        bool exists;
        string did;
        bytes rsaPublicKey;
    }

    struct Credential {
        address holder;
        address issuer;
        string portraitCid;
        string diplomaCid;
        string metadataCid;
        bytes wrappedKeyForHolder;
        bytes wrappedKeyForIssuer;
        bytes32 docHash;
        bytes issuerSignature;
        CredentialStatus status;
        uint64 issuedAt;
        uint64 revokedAt;
        bool sbtMinted;
    }

    struct Consent {
        bool active;
        bytes wrappedKeyForVerifier;
    }

    IdentitySBT public immutable identitySBT;
    uint256 private _nextCredentialId = 1;
    mapping(address => Identity) public identities;
    mapping(uint256 => Credential) private _credentials;
    mapping(uint256 => mapping(address => Consent)) private _consents;

    event KeyRegistered(address indexed account);
    event DIDCreated(address indexed holder, string did);
    event CredentialRequested(uint256 indexed credentialId, address indexed holder);
    event CredentialIssued(uint256 indexed credentialId, address indexed issuer, bytes32 docHash);
    event CredentialRevoked(uint256 indexed credentialId, address indexed issuer);
    event SBTMinted(uint256 indexed credentialId, address indexed holder);
    event ConsentGranted(uint256 indexed credentialId, address indexed verifier);
    event ConsentRevoked(uint256 indexed credentialId, address indexed verifier);

    constructor(address admin, address sbtAddress) {
        require(admin != address(0) && sbtAddress != address(0), "zero address");
        identitySBT = IdentitySBT(sbtAddress);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function registerKey(bytes calldata rsaPublicKey) external {
        require(rsaPublicKey.length > 0, "empty key");
        identities[msg.sender].rsaPublicKey = rsaPublicKey;
        emit KeyRegistered(msg.sender);
    }

    function createDID(string calldata did) external {
        require(!identities[msg.sender].exists, "DID exists");
        require(bytes(did).length > 0, "empty DID");
        identities[msg.sender].exists = true;
        identities[msg.sender].did = did;
        emit DIDCreated(msg.sender, did);
    }

    /// @return credentialId ID tăng dần do contract sinh, bắt đầu từ 1.
    function requestCredential(
        string calldata portraitCid,
        string calldata diplomaCid,
        string calldata metadataCid,
        bytes calldata wrappedKeyForHolder,
        bytes calldata wrappedKeyForIssuer
    ) external returns (uint256 credentialId) {
        require(identities[msg.sender].exists, "DID missing");
        require(bytes(portraitCid).length > 0 && bytes(diplomaCid).length > 0 && bytes(metadataCid).length > 0, "CID missing");
        require(wrappedKeyForHolder.length > 0 && wrappedKeyForIssuer.length > 0, "wrapped key missing");

        credentialId = _nextCredentialId++;
        Credential storage c = _credentials[credentialId];
        c.holder = msg.sender;
        c.portraitCid = portraitCid;
        c.diplomaCid = diplomaCid;
        c.metadataCid = metadataCid;
        c.wrappedKeyForHolder = wrappedKeyForHolder;
        c.wrappedKeyForIssuer = wrappedKeyForIssuer;
        c.status = CredentialStatus.REQUESTED;
        emit CredentialRequested(credentialId, msg.sender);
    }

    function signingDigest(uint256 credentialId, bytes32 docHash) public view returns (bytes32) {
        Credential storage c = _credentials[credentialId];
        return keccak256(abi.encode(address(this), block.chainid, credentialId, c.holder, docHash));
    }

    function issueCredential(uint256 credentialId, bytes32 docHash, bytes calldata signature)
        external
        onlyRole(ISSUER_ROLE)
    {
        Credential storage c = _credentials[credentialId];
        require(c.status == CredentialStatus.REQUESTED, "not requested");
        require(docHash != bytes32(0), "empty hash");
        address signer = ECDSA.recover(signingDigest(credentialId, docHash).toEthSignedMessageHash(), signature);
        require(signer == msg.sender, "bad issuer signature");
        c.issuer = msg.sender;
        c.docHash = docHash;
        c.issuerSignature = signature;
        c.status = CredentialStatus.ISSUED;
        c.issuedAt = uint64(block.timestamp);
        emit CredentialIssued(credentialId, msg.sender, docHash);
    }

    function mintSBT(uint256 credentialId) external {
        Credential storage c = _credentials[credentialId];
        require(c.status == CredentialStatus.ISSUED, "not issued");
        require(c.issuer == msg.sender, "not credential issuer");
        require(!c.sbtMinted, "already minted");
        c.sbtMinted = true;
        identitySBT.mint(c.holder, credentialId);
        emit SBTMinted(credentialId, c.holder);
    }

    function revokeCredential(uint256 credentialId) external {
        Credential storage c = _credentials[credentialId];
        require(c.status == CredentialStatus.ISSUED, "not issued");
        require(c.issuer == msg.sender, "not credential issuer");
        c.status = CredentialStatus.REVOKED;
        c.revokedAt = uint64(block.timestamp);
        if (c.sbtMinted) {
            c.sbtMinted = false;
            identitySBT.burn(credentialId);
        }
        emit CredentialRevoked(credentialId, msg.sender);
    }

    function grantConsent(uint256 credentialId, address verifier, bytes calldata wrappedKeyForVerifier) external {
        Credential storage c = _credentials[credentialId];
        require(c.holder == msg.sender, "not holder");
        require(c.status == CredentialStatus.ISSUED, "not issued");
        require(verifier != address(0) && wrappedKeyForVerifier.length > 0, "invalid consent");
        _consents[credentialId][verifier] = Consent(true, wrappedKeyForVerifier);
        emit ConsentGranted(credentialId, verifier);
    }

    function revokeConsent(uint256 credentialId, address verifier) external {
        require(_credentials[credentialId].holder == msg.sender, "not holder");
        _consents[credentialId][verifier].active = false;
        emit ConsentRevoked(credentialId, verifier);
    }

    function hasAccess(uint256 credentialId, address verifier) external view returns (bool) {
        return _credentials[credentialId].status == CredentialStatus.ISSUED && _consents[credentialId][verifier].active;
    }

    function getConsent(uint256 credentialId, address verifier) external view returns (bool active, bytes memory wrappedKey) {
        Consent storage consent = _consents[credentialId][verifier];
        return (consent.active && _credentials[credentialId].status == CredentialStatus.ISSUED, consent.wrappedKeyForVerifier);
    }

    function getCredential(uint256 credentialId) external view returns (Credential memory) {
        return _credentials[credentialId];
    }

    function verifyCredential(uint256 credentialId)
        external
        view
        returns (bool valid, address holder, address issuer, CredentialStatus status, bytes32 docHash)
    {
        Credential storage c = _credentials[credentialId];
        return (c.status == CredentialStatus.ISSUED, c.holder, c.issuer, c.status, c.docHash);
    }
}
