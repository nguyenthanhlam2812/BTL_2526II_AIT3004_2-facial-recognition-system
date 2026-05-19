import { describe, expect, it } from "vitest";
import { canOperate, isOwner } from "./access";

describe("canOperate", () => {
  it("returns true for owner and admin", () => {
    expect(canOperate("owner")).toBe(true);
    expect(canOperate("admin")).toBe(true);
  });

  it("returns false for viewer", () => {
    expect(canOperate("viewer")).toBe(false);
  });

  it("returns false for null or undefined", () => {
    expect(canOperate(null)).toBe(false);
    expect(canOperate(undefined)).toBe(false);
  });
});

describe("isOwner", () => {
  it("returns true only for the owner role", () => {
    expect(isOwner("owner")).toBe(true);
    expect(isOwner("admin")).toBe(false);
    expect(isOwner("viewer")).toBe(false);
    expect(isOwner(null)).toBe(false);
    expect(isOwner(undefined)).toBe(false);
  });
});
