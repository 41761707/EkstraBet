/** In-flight lock shared by admin user and league mutations. */

/** Returns false when another admin mutation is already in flight. */
export function acquireAdminMutationLock(lock: { current: boolean }): boolean {
  if (lock.current) {
    return false;
  }
  lock.current = true;
  return true;
}

export function releaseAdminMutationLock(lock: { current: boolean }): void {
  lock.current = false;
}
