
import { expect } from "chai";
import { ethers } from "hardhat";
import type { ContractRunner } from "ethers";
import { Contract } from "ethers";

type Credential = [
  string,
  string,
  string,
  string,
  string,
  string,
  string,
  string,
  string,
  bigint,
  bigint,
  bigint,
  boolean,
] & {
  holder: string;
  issuer: string;
  docHash: string;
  status: bigint;
  issuedAt: bigint;
  revokedAt: bigint;
  sbtMinted: boolean;
};

type Verification = [boolean, string, string, bigint, string] & {
  valid: boolean;
  holder: string;
  issuer: string;
  status: bigint;
  docHash: string;
};

type Consent = [boolean, string] & {
  active: boolean;
  wrappedKey: string;
};

class TypedContract {
  constructor(readonly raw: Contract) {}

  getAddress() {
    return this.raw.getAddress();
  }
}

function readString(value: unknown, label: string): string {
  if (typeof value !== "string") throw new Error(`Unexpected ${label} return type`);
  return value;
}

function readBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") throw new Error(`Unexpected ${label} return type`);
  return value;
}

function readBigint(value: unknown, label: string): bigint {
  if (typeof value !== "bigint") throw new Error(`Unexpected ${label} return type`);
  return value;
}

function readTuple(value: unknown, size: number, label: string): unknown[] {
  if (!Array.isArray(value) || value.length !== size) {
    throw new Error(`Unexpected ${label} return value`);
  }
  return value;
}

class IdentitySbtContract extends TypedContract {
  async DEFAULT_ADMIN_ROLE() { return readString(await this.raw.getFunction("DEFAULT_ADMIN_ROLE()").staticCall(), "DEFAULT_ADMIN_ROLE"); }
  async REGISTRY_ROLE() { return readString(await this.raw.getFunction("REGISTRY_ROLE()").staticCall(), "REGISTRY_ROLE"); }
  async hasRole(role: string, account: string) { return readBoolean(await this.raw.getFunction("hasRole(bytes32,address)").staticCall(role, account), "hasRole"); }
  setRegistry(registry: string) { return this.raw.getFunction("setRegistry(address)").send(registry); }
  grantRole(role: string, account: string) { return this.raw.getFunction("grantRole(bytes32,address)").send(role, account); }
  revokeRole(role: string, account: string) { return this.raw.getFunction("revokeRole(bytes32,address)").send(role, account); }
  async balanceOf(account: string) { return readBigint(await this.raw.getFunction("balanceOf(address)").staticCall(account), "balanceOf"); }
  async ownerOf(tokenId: bigint | number) { return readString(await this.raw.getFunction("ownerOf(uint256)").staticCall(tokenId), "ownerOf"); }
  transferFrom(from: string, to: string, tokenId: bigint | number) { return this.raw.getFunction("transferFrom(address,address,uint256)").send(from, to, tokenId); }

  connect(runner: ContractRunner | null) {
    return new IdentitySbtContract(new Contract(this.raw.target, this.raw.interface, runner));
  }
}

class RegistryContract extends TypedContract {
  async ISSUER_ROLE() { return readString(await this.raw.getFunction("ISSUER_ROLE()").staticCall(), "ISSUER_ROLE"); }
  async hasRole(role: string, account: string) { return readBoolean(await this.raw.getFunction("hasRole(bytes32,address)").staticCall(role, account), "hasRole"); }
  grantRole(role: string, account: string) { return this.raw.getFunction("grantRole(bytes32,address)").send(role, account); }
  revokeRole(role: string, account: string) { return this.raw.getFunction("revokeRole(bytes32,address)").send(role, account); }
  registerKey(publicKey: string) { return this.raw.getFunction("registerKey(bytes)").send(publicKey); }
  createDID(did: string) { return this.raw.getFunction("createDID(string)").send(did); }
  requestCredential(portrait: string, diploma: string, metadata: string, holderKey: string, issuerKey: string) { return this.raw.getFunction("requestCredential(string,string,string,bytes,bytes)").send(portrait, diploma, metadata, holderKey, issuerKey); }
  async signingDigest(credentialId: bigint | number, docHash: string) { return readString(await this.raw.getFunction("signingDigest(uint256,bytes32)").staticCall(credentialId, docHash), "signingDigest"); }
  issueCredential(credentialId: bigint | number, docHash: string, signature: string) { return this.raw.getFunction("issueCredential(uint256,bytes32,bytes)").send(credentialId, docHash, signature); }
  mintSBT(credentialId: bigint | number) { return this.raw.getFunction("mintSBT(uint256)").send(credentialId); }
  revokeCredential(credentialId: bigint | number) { return this.raw.getFunction("revokeCredential(uint256)").send(credentialId); }
  grantConsent(credentialId: bigint | number, verifier: string, key: string) { return this.raw.getFunction("grantConsent(uint256,address,bytes)").send(credentialId, verifier, key); }
  revokeConsent(credentialId: bigint | number, verifier: string) { return this.raw.getFunction("revokeConsent(uint256,address)").send(credentialId, verifier); }
  async hasAccess(credentialId: bigint | number, verifier: string) { return readBoolean(await this.raw.getFunction("hasAccess(uint256,address)").staticCall(credentialId, verifier), "hasAccess"); }
  async getConsent(credentialId: bigint | number, verifier: string): Promise<Consent> {
    const value = readTuple(await this.raw.getFunction("getConsent(uint256,address)").staticCall(credentialId, verifier), 2, "getConsent");
    const consent = [readBoolean(value[0], "consent active"), readString(value[1], "consent key")] as Consent;
    return Object.assign(consent, { active: consent[0], wrappedKey: consent[1] });
  }
  async getCredential(credentialId: bigint | number): Promise<Credential> {
    const value = readTuple(await this.raw.getFunction("getCredential(uint256)").staticCall(credentialId), 13, "getCredential");
    const credential = [
      readString(value[0], "holder"), readString(value[1], "issuer"), readString(value[2], "portrait CID"),
      readString(value[3], "diploma CID"), readString(value[4], "metadata CID"), readString(value[5], "holder key"),
      readString(value[6], "issuer key"), readString(value[7], "doc hash"), readString(value[8], "signature"),
      readBigint(value[9], "status"), readBigint(value[10], "issued time"), readBigint(value[11], "revoked time"), readBoolean(value[12], "SBT minted"),
    ] as Credential;
    return Object.assign(credential, { holder: credential[0], issuer: credential[1], docHash: credential[7], status: credential[9], issuedAt: credential[10], revokedAt: credential[11], sbtMinted: credential[12] });
  }
  async verifyCredential(credentialId: bigint | number): Promise<Verification> {
    const value = readTuple(await this.raw.getFunction("verifyCredential(uint256)").staticCall(credentialId), 5, "verifyCredential");
    const verification = [readBoolean(value[0], "valid"), readString(value[1], "holder"), readString(value[2], "issuer"), readBigint(value[3], "status"), readString(value[4], "doc hash")] as Verification;
    return Object.assign(verification, { valid: verification[0], holder: verification[1], issuer: verification[2], status: verification[3], docHash: verification[4] });
  }

  connect(runner: ContractRunner | null) {
    return new RegistryContract(new Contract(this.raw.target, this.raw.interface, runner));
  }
}

class GatedServiceContract extends TypedContract {
  accessService(credentialId: bigint | number) { return this.raw.getFunction("accessService(uint256)").send(credentialId); }

  connect(runner: ContractRunner | null) {
    return new GatedServiceContract(new Contract(this.raw.target, this.raw.interface, runner));
  }
}

type TestSigner = ContractRunner & { address: string };

async function deploySbt(admin: TestSigner): Promise<IdentitySbtContract> {
  const deployed = await ethers.deployContract("IdentitySBT", [admin.address]);
  await deployed.waitForDeployment();
  return new IdentitySbtContract(new Contract(await deployed.getAddress(), deployed.interface, admin));
}

async function deployRegistry(admin: TestSigner, sbt: IdentitySbtContract): Promise<RegistryContract> {
  const deployed = await ethers.deployContract("SSIRegistry", [admin.address, await sbt.getAddress()]);
  await deployed.waitForDeployment();
  return new RegistryContract(new Contract(await deployed.getAddress(), deployed.interface, admin));
}

async function deployGate(sbt: IdentitySbtContract, registry: RegistryContract): Promise<GatedServiceContract> {
  const deployed = await ethers.deployContract("GatedService", [await sbt.getAddress(), await registry.getAddress()]);
  await deployed.waitForDeployment();
  return new GatedServiceContract(new Contract(await deployed.getAddress(), deployed.interface, sbt.raw.runner));
}

describe("SSI MVP contracts", function () {
  async function fixture() {
    const [admin, holder, issuer, verifier, attacker] =
      await ethers.getSigners();

    const sbt = await deploySbt(admin);

    const registry = await deployRegistry(admin, sbt);

    await sbt.setRegistry(await registry.getAddress());

    const gate = await deployGate(sbt, registry);

    await registry.grantRole(
      await registry.ISSUER_ROLE(),
      issuer.address
    );

    return {
      admin,
      holder,
      issuer,
      verifier,
      attacker,
      sbt,
      registry,
      gate,
    };
  }

  // =========================================================
  // TEST 1: Credential lifecycle + SBT + Gated Service
  // =========================================================

  it("chạy vòng đời REQUESTED -> ISSUED -> REVOKED và gate", async function () {
    const { holder, issuer, sbt, registry, gate } = await fixture();

    // Holder đăng ký RSA public key và DID.
    await registry.connect(holder).registerKey("0x1234");

    await registry
      .connect(holder)
      .createDID(`did:ssi:${holder.address.toLowerCase()}`);

    // Holder gửi yêu cầu Credential.
    await expect(
      registry
        .connect(holder)
        .requestCredential(
          "cid-jpg",
          "cid-pdf",
          "cid-json",
          "0xaa",
          "0xbb"
        )
    )
      .to.emit(registry.raw, "CredentialRequested")
      .withArgs(1n, holder.address);

    // Issuer ký và phát hành Credential.
    const docHash = ethers.sha256(
      ethers.toUtf8Bytes("fake diploma")
    );

    const digest = await registry.signingDigest(1, docHash);

    const signature = await issuer.signMessage(
      ethers.getBytes(digest)
    );

    await registry
      .connect(issuer)
      .issueCredential(1, docHash, signature);

    expect((await registry.verifyCredential(1))[0]).to.equal(true);

    // Issuer mint SBT.
    await registry.connect(issuer).mintSBT(1);

    // Xác nhận SBT đã được mint cho đúng Holder.
    expect(await sbt.ownerOf(1)).to.equal(holder.address);

    // Holder không thể chuyển SBT sang ví khác.
    await expect(
      sbt
        .connect(holder)
        .transferFrom(holder.address, issuer.address, 1)
    ).to.be.revertedWithCustomError(sbt.raw, "Soulbound");

    // Holder có thể sử dụng Gated Service.
    await expect(
      gate.connect(holder).accessService(1)
    )
      .to.emit(gate.raw, "ServiceAccessed")
      .withArgs(holder.address, 1n);

    // Issuer revoke Credential.
    await registry.connect(issuer).revokeCredential(1);

    expect((await registry.verifyCredential(1))[0]).to.equal(false);

    // SBT bị burn sau khi Credential bị revoke.
    await expect(sbt.ownerOf(1)).to.be.reverted;
  });

  // =========================================================
  // TEST 2: Unauthorized issuer + original issuer protection
  // =========================================================

  it("chặn ví không có ISSUER_ROLE và issuer khác thu hồi", async function () {
    const { holder, issuer, attacker, registry } = await fixture();

    await registry
      .connect(holder)
      .createDID("did:ssi:holder");

    await registry
      .connect(holder)
      .requestCredential("a", "b", "c", "0xaa", "0xbb");

    const hash = ethers.sha256(
      ethers.toUtf8Bytes("demo")
    );

    // Attacker không có ISSUER_ROLE: không thể phát hành.
    const badSignature = await attacker.signMessage(
      ethers.getBytes(await registry.signingDigest(1, hash))
    );

    await expect(
      registry
        .connect(attacker)
        .issueCredential(1, hash, badSignature)
    ).to.be.reverted;

    // Issuer hợp lệ phát hành Credential.
    const signature = await issuer.signMessage(
      ethers.getBytes(await registry.signingDigest(1, hash))
    );

    await registry
      .connect(issuer)
      .issueCredential(1, hash, signature);

    // Attacker không có ISSUER_ROLE: không thể revoke.
    await expect(
      registry.connect(attacker).revokeCredential(1)
    ).to.be.reverted;

    // Cấp ISSUER_ROLE cho attacker để kiểm tra lớp bảo vệ thứ hai.
    await registry.grantRole(
      await registry.ISSUER_ROLE(),
      attacker.address
    );

    // Có role nhưng không phải Issuer ban đầu: vẫn không thể revoke.
    await expect(
      registry.connect(attacker).revokeCredential(1)
    ).to.be.revertedWith("not credential issuer");
  });

  // =========================================================
  // TEST 3: DL-02 - One DID can have multiple credentials
  // =========================================================

  it("DL-02: một DID có thể tạo nhiều Credential", async function () {
    const { holder, registry } = await fixture();

    await registry
      .connect(holder)
      .createDID("did:ssi:holder");

    await expect(
      registry
        .connect(holder)
        .requestCredential("p1", "d1", "m1", "0xaa", "0xbb")
    )
      .to.emit(registry.raw, "CredentialRequested")
      .withArgs(1n, holder.address);

    await expect(
      registry
        .connect(holder)
        .requestCredential("p2", "d2", "m2", "0xcc", "0xdd")
    )
      .to.emit(registry.raw, "CredentialRequested")
      .withArgs(2n, holder.address);

    const credential1 = await registry.getCredential(1);
    const credential2 = await registry.getCredential(2);

    expect(credential1.holder).to.equal(holder.address);
    expect(credential2.holder).to.equal(holder.address);

    expect(credential1.status).to.equal(1n);
    expect(credential2.status).to.equal(1n);
  });

  it("chặn tài khoản có ISSUER_ROLE khi chữ ký không thuộc caller", async function () {
    const { holder, issuer, attacker, registry } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const role = await registry.ISSUER_ROLE();
    await registry.grantRole(role, attacker.address);
    expect(await registry.hasRole(role, attacker.address)).to.equal(true);

    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await expect(registry.connect(attacker).issueCredential(1, docHash, signature))
      .to.be.revertedWith("bad issuer signature");

    const credential = await registry.getCredential(1);
    expect(credential.status).to.equal(1n);
    expect(credential.issuer).to.equal(ethers.ZeroAddress);
    expect(credential.docHash).to.equal(ethers.ZeroHash);
  });

  // =========================================================
  // TEST 4: DL-03 - Issuer loses and regains role
  // =========================================================

  it("DL-03: Issuer mất role không thể mint hoặc revoke", async function () {
    const { admin, holder, issuer, registry } = await fixture();

    await registry
      .connect(holder)
      .createDID("did:ssi:holder");

    await registry
      .connect(holder)
      .requestCredential(
        "portrait",
        "diploma",
        "metadata",
        "0xaa",
        "0xbb"
      );

    const hash = ethers.sha256(
      ethers.toUtf8Bytes("demo")
    );

    const digest = await registry.signingDigest(1, hash);

    const signature = await issuer.signMessage(
      ethers.getBytes(digest)
    );

    await registry
      .connect(issuer)
      .issueCredential(1, hash, signature);

    const issuerRole = await registry.ISSUER_ROLE();

    // Admin thu hồi quyền Issuer.
    await registry.revokeRole(issuerRole, issuer.address);

    // Issuer mất role nên không thể mint.
    await expect(
      registry.connect(issuer).mintSBT(1)
    ).to.be.reverted;

    // Issuer mất role nên không thể revoke.
    await expect(
      registry.connect(issuer).revokeCredential(1)
    ).to.be.reverted;

    // Admin cấp lại role.
    await registry.grantRole(issuerRole, issuer.address);

    // Issuer ban đầu có thể mint và revoke trở lại.
    await registry.connect(issuer).mintSBT(1);

    await registry.connect(issuer).revokeCredential(1);

    expect((await registry.verifyCredential(1))[3]).to.equal(3n);
  });

  // =========================================================
  // TEST 5: DL-04 - One-time Registry binding
  // =========================================================

  it("DL-04: chỉ cho phép liên kết một Registry", async function () {
    const { admin, attacker, sbt, registry } = await fixture();

    const registryRole = await sbt.REGISTRY_ROLE();

    // Registry ban đầu đã được liên kết.
    expect(
      await sbt.hasRole(
        registryRole,
        await registry.getAddress()
      )
    ).to.equal(true);

    // Không thể liên kết Registry thứ hai.
    await expect(
      sbt.connect(admin).setRegistry(attacker.address)
    ).to.be.revertedWith("registry already set");

    // Không thể cấp REGISTRY_ROLE trực tiếp.
    await expect(
      sbt.connect(admin).grantRole(
        registryRole,
        attacker.address
      )
    ).to.be.revertedWith("use setRegistry");

    expect(
      await sbt.hasRole(registryRole, attacker.address)
    ).to.equal(false);
  });

  // =========================================================
  // TEST 6: DL-05 - RSA public key is immutable
  // =========================================================

  it("DL-05: không thể thay đổi RSA public key sau khi đăng ký", async function () {
    const { holder, registry } = await fixture();

    // Đăng ký public key lần đầu.
    await expect(
      registry.connect(holder).registerKey("0x1234")
    )
      .to.emit(registry.raw, "KeyRegistered")
      .withArgs(holder.address);

    // Không thể đăng ký public key lần thứ hai.
    await expect(
      registry.connect(holder).registerKey("0xabcd")
    ).to.be.revertedWith("key already registered");
  });

  it("Round 1 A: từ chối docHash bằng zero", async function () {
    const { holder, issuer, registry } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    expect(await registry.hasRole(await registry.ISSUER_ROLE(), issuer.address)).to.equal(true);
    const docHash = ethers.ZeroHash;
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await expect(registry.connect(issuer).issueCredential(1, docHash, signature))
      .to.be.revertedWith("empty hash");

    const credential = await registry.getCredential(1);
    expect(credential.status).to.equal(1n);
    expect(credential.issuer).to.equal(ethers.ZeroAddress);
    expect(credential.docHash).to.equal(ethers.ZeroHash);
  });

  it("Round 1 B: Issuer khác có role vẫn bị từ chối mint", async function () {
    const { holder, issuer, attacker: issuerB, registry, sbt } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    const role = await registry.ISSUER_ROLE();
    await registry.grantRole(role, issuerB.address);
    expect(await registry.hasRole(role, issuerB.address)).to.equal(true);
    const before = await registry.getCredential(1);
    expect(before.status).to.equal(2n);
    expect(before.sbtMinted).to.equal(false);

    await expect(registry.connect(issuerB).mintSBT(1)).to.be.revertedWith("not credential issuer");
    expect(await registry.getCredential(1)).to.deep.equal(before);
    expect(await sbt.balanceOf(holder.address)).to.equal(0n);
    await expect(sbt.ownerOf(1)).to.be.revertedWithCustomError(sbt.raw, "ERC721NonexistentToken").withArgs(1n);
  });

  it("Round 1 C: từ chối mint SBT lần thứ hai", async function () {
    const { holder, issuer, registry, sbt } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    await registry.connect(issuer).mintSBT(1);
    const balance = await sbt.balanceOf(holder.address);
    expect(balance).to.equal(1n);

    await expect(registry.connect(issuer).mintSBT(1)).to.be.revertedWith("already minted");
    expect(await sbt.ownerOf(1)).to.equal(holder.address);
    expect(await sbt.balanceOf(holder.address)).to.equal(balance);
    expect((await registry.getCredential(1)).sbtMinted).to.equal(true);
  });

  it("Round 2 A: verify nonexistent", async function () {
    const { registry } = await fixture();
    expect(await registry.verifyCredential(0)).to.deep.equal([
      false, ethers.ZeroAddress, ethers.ZeroAddress, 0n, ethers.ZeroHash,
    ]);
  });

  it("Round 2 B: verify REQUESTED", async function () {
    const { registry, holder } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    expect(await registry.verifyCredential(1)).to.deep.equal([
      false, holder.address, ethers.ZeroAddress, 1n, ethers.ZeroHash,
    ]);
  });

  it("Round 2 C: wrong SBT holder", async function () {
    const { holder, issuer, verifier, registry, sbt, gate } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    await registry.connect(issuer).mintSBT(1);
    expect(await sbt.ownerOf(1)).to.equal(holder.address);
    await expect(gate.connect(verifier).accessService(1)).to.be.revertedWith("not SBT holder");
  });

  it("Round 2 D: access after revoke", async function () {
    const { holder, issuer, registry, sbt, gate } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    await registry.connect(issuer).mintSBT(1);
    expect(await sbt.ownerOf(1)).to.equal(holder.address);
    await registry.connect(issuer).revokeCredential(1);
    const result = await registry.verifyCredential(1);
    expect(result.valid).to.equal(false);
    expect(result.status).to.equal(3n);
    await expect(sbt.ownerOf(1)).to.be.revertedWithCustomError(sbt.raw, "ERC721NonexistentToken").withArgs(1n);
    await expect(gate.connect(holder).accessService(1))
      .to.be.revertedWithCustomError(sbt.raw, "ERC721NonexistentToken").withArgs(1n);
  });

  it("Round 3 A: Grant Consent", async function () {
    const { registry, holder, issuer, verifier } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    await registry.connect(issuer).mintSBT(1);
    const wrappedKey = "0x1234abcd";

    await expect(registry.connect(holder).grantConsent(1, verifier.address, wrappedKey))
      .to.emit(registry.raw, "ConsentGranted").withArgs(1n, verifier.address);
    expect(await registry.hasAccess(1, verifier.address)).to.equal(true);
    expect(await registry.getConsent(1, verifier.address)).to.deep.equal([true, wrappedKey]);
  });

  it("Round 3 B: Revoke Consent", async function () {
    const { registry, holder, issuer, verifier } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    const wrappedKey = "0x1234abcd";
    await registry.connect(holder).grantConsent(1, verifier.address, wrappedKey);
    expect(await registry.hasAccess(1, verifier.address)).to.equal(true);

    await expect(registry.connect(holder).revokeConsent(1, verifier.address))
      .to.emit(registry.raw, "ConsentRevoked").withArgs(1n, verifier.address);
    expect(await registry.hasAccess(1, verifier.address)).to.equal(false);
    expect(await registry.getConsent(1, verifier.address)).to.deep.equal([false, wrappedKey]);
  });

  it("Round 3 C: Non-holder grant", async function () {
    const { registry, holder, issuer, verifier, attacker } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    await registry.connect(issuer).mintSBT(1);
    const wrappedKey = "0x1234abcd";

    await expect(registry.connect(attacker).grantConsent(1, verifier.address, wrappedKey))
      .to.be.revertedWith("not holder");
    expect(await registry.hasAccess(1, verifier.address)).to.equal(false);
    expect(await registry.getConsent(1, verifier.address)).to.deep.equal([false, "0x"]);
  });

  it("Round 3 D: Non-holder revoke", async function () {
    const { registry, holder, issuer, verifier, attacker } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    const wrappedKey = "0x1234abcd";
    await registry.connect(holder).grantConsent(1, verifier.address, wrappedKey);
    expect(await registry.hasAccess(1, verifier.address)).to.equal(true);

    await expect(registry.connect(attacker).revokeConsent(1, verifier.address))
      .to.be.revertedWith("not holder");
    expect(await registry.hasAccess(1, verifier.address)).to.equal(true);
    expect(await registry.getConsent(1, verifier.address)).to.deep.equal([true, wrappedKey]);
  });

  it("Round 3 E: Grant before ISSUED", async function () {
    const { registry, holder, verifier } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const wrappedKey = "0x1234abcd";

    await expect(registry.connect(holder).grantConsent(1, verifier.address, wrappedKey))
      .to.be.revertedWith("not issued");
    expect(await registry.hasAccess(1, verifier.address)).to.equal(false);
    expect(await registry.getConsent(1, verifier.address)).to.deep.equal([false, "0x"]);
    expect((await registry.getCredential(1)).status).to.equal(1n);
  });

  it("Round 3 F: Zero-address Verifier", async function () {
    const { registry, holder, issuer } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);
    const wrappedKey = "0x1234abcd";

    await expect(registry.connect(holder).grantConsent(1, ethers.ZeroAddress, wrappedKey))
      .to.be.revertedWith("invalid consent");
    expect(await registry.hasAccess(1, ethers.ZeroAddress)).to.equal(false);
    expect(await registry.getConsent(1, ethers.ZeroAddress)).to.deep.equal([false, "0x"]);
  });

  it("Round 3 G: Empty wrapped key", async function () {
    const { registry, holder, issuer, verifier } = await fixture();
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const docHash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, docHash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, docHash, signature);

    await expect(registry.connect(holder).grantConsent(1, verifier.address, "0x"))
      .to.be.revertedWith("invalid consent");
    expect(await registry.hasAccess(1, verifier.address)).to.equal(false);
    expect(await registry.getConsent(1, verifier.address)).to.deep.equal([false, "0x"]);
  });

  async function issuedRegistryFixture() {
    const context = await fixture();
    const { registry, holder, issuer, sbt } = context;
    await registry.connect(holder).createDID("did:ssi:holder");
    await registry.connect(holder).requestCredential("portrait", "diploma", "metadata", "0xaa", "0xbb");
    const hash = ethers.sha256(ethers.toUtf8Bytes("demo diploma"));
    const digest = await registry.signingDigest(1, hash);
    const signature = await issuer.signMessage(ethers.getBytes(digest));
    await registry.connect(issuer).issueCredential(1, hash, signature);
    return { ...context, role: await sbt.REGISTRY_ROLE(), address: await registry.getAddress() };
  }

  it("Round 4 A: revoke Registry role and reject rebinding", async function () {
    const { admin, registry, sbt, attacker } = await fixture();
    const address = await registry.getAddress();
    const role = await sbt.REGISTRY_ROLE();
    expect(await sbt.hasRole(role, address)).to.equal(true);
    await sbt.connect(admin).revokeRole(role, address);
    expect(await sbt.hasRole(role, address)).to.equal(false);
    await expect(sbt.connect(admin).setRegistry(attacker.address)).to.be.revertedWith("registry already set");
    await expect(sbt.connect(admin).grantRole(role, address)).to.be.revertedWith("use setRegistry");
  });

  it("Round 4 B: mint rolls back after Registry role loss", async function () {
    const { admin, issuer, holder, registry, sbt, role, address } = await issuedRegistryFixture();
    await sbt.connect(admin).revokeRole(role, address);
    await expect(registry.connect(issuer).mintSBT(1))
      .to.be.revertedWithCustomError(sbt.raw, "AccessControlUnauthorizedAccount").withArgs(address, role);
    const credential = await registry.getCredential(1);
    expect(credential.status).to.equal(2n);
    expect(credential.sbtMinted).to.equal(false);
    expect(await sbt.balanceOf(holder.address)).to.equal(0n);
    await expect(sbt.ownerOf(1)).to.be.revertedWithCustomError(sbt.raw, "ERC721NonexistentToken").withArgs(1n);
  });

  it("Round 4 C: failed burn rolls back credential revocation", async function () {
    const { admin, issuer, holder, registry, sbt, role, address } = await issuedRegistryFixture();
    await registry.connect(issuer).mintSBT(1);
    expect(await sbt.ownerOf(1)).to.equal(holder.address);
    await sbt.connect(admin).revokeRole(role, address);
    await expect(registry.connect(issuer).revokeCredential(1))
      .to.be.revertedWithCustomError(sbt.raw, "AccessControlUnauthorizedAccount").withArgs(address, role);
    const credential = await registry.getCredential(1);
    expect(credential.status).to.equal(2n);
    expect(credential.revokedAt).to.equal(0n);
    expect(credential.sbtMinted).to.equal(true);
    expect((await registry.verifyCredential(1)).valid).to.equal(true);
    expect(await sbt.ownerOf(1)).to.equal(holder.address);
  });

  it("Round 4 D: existing SBT survives Registry role loss", async function () {
    const { admin, issuer, holder, registry, sbt, role, address } = await issuedRegistryFixture();
    await registry.connect(issuer).mintSBT(1);
    const balance = await sbt.balanceOf(holder.address);
    expect(balance).to.equal(1n);
    await sbt.connect(admin).revokeRole(role, address);
    expect(await sbt.hasRole(role, address)).to.equal(false);
    expect(await sbt.ownerOf(1)).to.equal(holder.address);
    expect(await sbt.balanceOf(holder.address)).to.equal(balance);
  });

  it("Round 5 A: SSIRegistry rejects zero SBT", async function () {
    const [admin] = await ethers.getSigners();
    await expect(ethers.deployContract("SSIRegistry", [admin.address, ethers.ZeroAddress]))
      .to.be.revertedWith("zero address");
  });

  it("Round 5 B: GatedService rejects zero SBT", async function () {
    const { registry } = await fixture();
    await expect(ethers.deployContract("GatedService", [ethers.ZeroAddress, await registry.getAddress()]))
      .to.be.revertedWith("zero address");
  });

  it("Round 5 C: GatedService rejects zero Registry", async function () {
    const { sbt } = await fixture();
    await expect(ethers.deployContract("GatedService", [await sbt.getAddress(), ethers.ZeroAddress]))
      .to.be.revertedWith("zero address");
  });

  it("Round 5 D: zero Registry does not consume the one-time binding", async function () {
    const [admin] = await ethers.getSigners();
    const sbt = await deploySbt(admin);
    const registry = await deployRegistry(admin, sbt);
    const address = await registry.getAddress();
    const role = await sbt.REGISTRY_ROLE();

    await expect(sbt.connect(admin).setRegistry(ethers.ZeroAddress)).to.be.revertedWith("registry=0");
    expect(await sbt.hasRole(role, ethers.ZeroAddress)).to.equal(false);
    await sbt.connect(admin).setRegistry(address);
    expect(await sbt.hasRole(role, address)).to.equal(true);
    await expect(sbt.connect(admin).setRegistry(address)).to.be.revertedWith("registry already set");
  });

  it("Round 5 E: IdentitySBT rejects zero Admin and grants authority to the configured Admin", async function () {
    const [admin] = await ethers.getSigners();
    await expect(ethers.deployContract("IdentitySBT", [ethers.ZeroAddress])).to.be.revertedWith("zero address");

    const sbt = await deploySbt(admin);
    const role = await sbt.DEFAULT_ADMIN_ROLE();
    expect(await sbt.hasRole(role, admin.address)).to.equal(true);
    expect(await sbt.hasRole(role, ethers.ZeroAddress)).to.equal(false);

    const registry = await deployRegistry(admin, sbt);
    const registryAddress = await registry.getAddress();
    await sbt.connect(admin).setRegistry(registryAddress);
    expect(await sbt.hasRole(await sbt.REGISTRY_ROLE(), registryAddress)).to.equal(true);
  });
});
