import { describe, expect, it } from "vitest";

import {
  acquireAdminMutationLock,
  releaseAdminMutationLock,
} from "@/components/admin/adminMutationLock";

describe("adminMutationLock", () => {
  it("rejects a second acquire while the lock is held", () => {
    const lock = { current: false };
    expect(acquireAdminMutationLock(lock)).toBe(true);
    expect(acquireAdminMutationLock(lock)).toBe(false);
    releaseAdminMutationLock(lock);
    expect(acquireAdminMutationLock(lock)).toBe(true);
  });
});
