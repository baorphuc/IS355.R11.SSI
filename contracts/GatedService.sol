// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IIdentitySBT {
    function ownerOf(uint256 tokenId) external view returns (address);
}

interface ISSIRegistry {
    function verifyCredential(uint256 credentialId)
        external view returns (bool valid, address holder, address issuer, uint8 status, bytes32 docHash);
}

contract GatedService {
    IIdentitySBT public immutable sbt;
    ISSIRegistry public immutable registry;

    event ServiceAccessed(address indexed user, uint256 indexed credentialId);

    constructor(address sbtAddress, address registryAddress) {
        require(sbtAddress != address(0) && registryAddress != address(0), "zero address");
        sbt = IIdentitySBT(sbtAddress);
        registry = ISSIRegistry(registryAddress);
    }

    function accessService(uint256 credentialId) external {
        require(sbt.ownerOf(credentialId) == msg.sender, "not SBT holder");
        (bool valid, address holder,, uint8 status,) = registry.verifyCredential(credentialId);
        require(valid && status == 2 && holder == msg.sender, "credential invalid");
        emit ServiceAccessed(msg.sender, credentialId);
    }
}
