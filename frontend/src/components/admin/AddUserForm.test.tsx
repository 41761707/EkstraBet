import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AddUserForm, ADD_USER_FORM_TITLE } from "@/components/admin/AddUserForm";

describe("AddUserForm", () => {
  it("renders username, temporary password, display name and admin fields", () => {
    const html = renderToStaticMarkup(
      <AddUserForm isSubmitting={false} onSubmit={async () => undefined} />,
    );

    expect(html).toContain(ADD_USER_FORM_TITLE);
    expect(html).toContain('name="username"');
    expect(html).toContain('name="temporary_password"');
    expect(html).toContain('name="display_name"');
    expect(html).toContain('name="is_admin"');
    expect(html).toContain("Nadaj rolę administratora");
    expect(html).toContain("Utwórz konto");
    expect(html).not.toContain("password_hash");
  });

  it("shows a creating label while the request is in flight", () => {
    const html = renderToStaticMarkup(
      <AddUserForm isSubmitting={true} onSubmit={async () => undefined} />,
    );

    expect(html).toContain("Tworzenie…");
    expect(html).toContain("disabled");
  });
});
