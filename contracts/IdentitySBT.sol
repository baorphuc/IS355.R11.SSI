// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

/// @notice SBT tối giản: Registry duy nhất được mint/burn, mọi transfer đều bị chặn.
contract IdentitySBT is ERC721, AccessControl {
    bytes32 public constant REGISTRY_ROLE = keccak256("REGISTRY_ROLE");

    error Soulbound();

    constructor(address admin) ERC721("SSI Identity SBT", "SSISBT") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function setRegistry(address registry) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(registry != address(0), "registry=0");
        _grantRole(REGISTRY_ROLE, registry);
    }

    function mint(address holder, uint256 credentialId) external onlyRole(REGISTRY_ROLE) {
        _safeMint(holder, credentialId);
    }

    function burn(uint256 credentialId) external onlyRole(REGISTRY_ROLE) {
        _burn(credentialId);
    }

    function _update(address to, uint256 tokenId, address auth)
        internal
        override
        returns (address)
    {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) revert Soulbound();
        return super._update(to, tokenId, auth);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
