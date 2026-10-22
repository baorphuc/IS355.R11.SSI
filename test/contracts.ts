import { expect } from "chai";
import { ethers } from "hardhat";

describe("SSI MVP contracts", function () {
  async function fixture() {
    const [admin, holder, issuer, verifier, attacker] = await ethers.getSigners();
    const sbt = await ethers.deployContract("IdentitySBT", [admin.address]);
    const registry = await ethers.deployContract("SSIRegistry", [admin.address, await sbt.getAddress()]);
    await sbt.setRegistry(await registry.getAddress());
    const gate = await ethers.deployContract("GatedService", [await sbt.getAddress(), await registry.getAddress()]);
    await registry.grantRole(await registry.ISSUER_ROLE(), issuer.address);
    return { admin, holder, issuer, verifier, attacker, sbt, registry, gate };
  }

  it("chạy vòng đời REQUESTED -> ISSUED -> REVOKED và gate", async function () {
    const { holder, issuer, sbt, registry, gate } = await fixture();
    await registry.connect(holder).registerKey("0x1234");
    await registry.connect(holder).createDID(`did:ssi:${holder.address.toLowerCase()}`);
    await expect(registry.connect(holder).requestCredential("cid-jpg", "cid-pdf", "cid-json", "0xaa", "0xbb"))
      .to.emit(registry, "CredentialRequested").withArgs(1n, holder.address);

    const docHash = ethers.sha256(ethers.toUtf8Bytes("fake diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    expect((await registry.verifyCredential(1))[0]).to.equal(true);

    await registry.connect(issuer).mintSBT(1);
    await expect(gate.connect(holder).accessService(1)).to.emit(gate, "ServiceAccessed").withArgs(holder.address, 1n);
    await expect(sbt.connect(holder).transferFrom(holder.address, issuer.address, 1)).to.be.revertedWithCustomError(sbt, "Soulbound");

    await registry.connect(issuer).revokeCredential(1);
    expect((await registry.verifyCredential(1))[0]).to.equal(false);
    await expect(sbt.ownerOf(1)).to.be.reverted;
  });

  it("chặn ví không có ISSUER_ROLE và issuer khác thu hồi", async function () {
    const { holder, issuer, attacker, registry } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("a", "b", "c", "0xaa", "0xbb");
    const hash = ethers.sha256(ethers.toUtf8Bytes("demo"));
    const badSignature = await attacker.signMessage(ethers.getBytes(await registry.signingDigest(1, hash)));
    await expect(registry.connect(attacker).issueCredential(1, hash, badSignature)).to.be.reverted;
    const signature = await issuer.signMessage(ethers.getBytes(await registry.signingDigest(1, hash)));
    await registry.connect(issuer).issueCredential(1, hash, signature);
    await expect(registry.connect(attacker).revokeCredential(1)).to.be.revertedWith("not credential issuer");
  });
});
