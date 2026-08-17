import { describe, expect, it } from "vitest";

import {
  decodeProfileUsername,
  isOwnProfile,
  profilePath,
} from "@/lib/profilePaths";

describe("profilePath", () => {
  it("builds a /profile URL with an encoded username", () => {
    expect(profilePath("alice")).toBe("/profile/alice");
    expect(profilePath("jan kowalski")).toBe("/profile/jan%20kowalski");
    expect(profilePath("żółć")).toBe(
      "/profile/%C5%BC%C3%B3%C5%82%C4%87",
    );
  });
});

describe("decodeProfileUsername", () => {
  it("decodes leftover percent-encoding in the route segment", () => {
    expect(decodeProfileUsername("alice")).toBe("alice");
    expect(decodeProfileUsername("jan%20kowalski")).toBe("jan kowalski");
  });
});

describe("isOwnProfile", () => {
  it("accepts the canonical username, including an encoded segment", () => {
    expect(isOwnProfile("alice", "alice")).toBe(true);
    expect(isOwnProfile("jan%20kowalski", "jan kowalski")).toBe(true);
  });

  it("rejects a foreign username segment without leaking ownership details", () => {
    expect(isOwnProfile("bob", "alice")).toBe(false);
    expect(isOwnProfile("Alice", "alice")).toBe(false);
    expect(isOwnProfile("", "alice")).toBe(false);
  });
});
