import { describe, expect, it } from "vitest";

import {
  mapCompleteFirstLoginError,
  validateFirstLoginForm,
} from "@/components/auth/firstLoginFormModel";

describe("validateFirstLoginForm", () => {
  it("accepts matching credentials within length limits", () => {
    expect(
      validateFirstLoginForm({
        username: " alice ",
        displayName: " Alice ",
        newPassword: "abc",
        newPasswordConfirm: "abc",
      }),
    ).toBeNull();
  });

  it("rejects a mismatched password confirmation", () => {
    expect(
      validateFirstLoginForm({
        username: "alice",
        displayName: "Alice",
        newPassword: "abc",
        newPasswordConfirm: "abd",
      }),
    ).toBe("Hasła nie są identyczne");
  });

  it("rejects a password shorter than 3 characters", () => {
    expect(
      validateFirstLoginForm({
        username: "alice",
        displayName: "Alice",
        newPassword: "ab",
        newPasswordConfirm: "ab",
      }),
    ).toBe("Hasło musi mieć od 3 do 200 znaków");
  });

  it("rejects an empty username after trim", () => {
    expect(
      validateFirstLoginForm({
        username: "   ",
        displayName: "Alice",
        newPassword: "abc",
        newPasswordConfirm: "abc",
      }),
    ).toBe("Nazwa użytkownika musi mieć od 1 do 50 znaków");
  });

  it("rejects an empty display name after trim", () => {
    expect(
      validateFirstLoginForm({
        username: "alice",
        displayName: "   ",
        newPassword: "abc",
        newPasswordConfirm: "abc",
      }),
    ).toBe("Wyświetlana nazwa musi mieć od 1 do 50 znaków");
  });
});

describe("mapCompleteFirstLoginError", () => {
  it("maps known API details to Polish messages", () => {
    expect(mapCompleteFirstLoginError("Username already taken")).toBe(
      "Nazwa użytkownika jest już zajęta",
    );
    expect(
      mapCompleteFirstLoginError(
        "Display name must be between 1 and 50 characters",
      ),
    ).toBe("Wyświetlana nazwa musi mieć od 1 do 50 znaków");
    expect(mapCompleteFirstLoginError("Passwords do not match")).toBe(
      "Hasła nie są identyczne",
    );
    expect(mapCompleteFirstLoginError("First login already completed")).toBe(
      "Konto zostało już uzupełnione",
    );
  });

  it("falls back when the API omits a detail", () => {
    expect(mapCompleteFirstLoginError(undefined)).toBe(
      "Nie udało się zapisać danych konta",
    );
  });
});
