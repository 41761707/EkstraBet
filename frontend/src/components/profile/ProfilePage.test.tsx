import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ProfilePage } from "@/components/profile/ProfilePage";
import { ProfileSection } from "@/components/profile/ProfileSection";

describe("ProfilePage", () => {
  it("renders the account header with display name and username", () => {
    const html = renderToStaticMarkup(
      <ProfilePage username="alice" displayName="Alicja" />,
    );

    expect(html).toContain("Alicja");
    expect(html).toContain("@alice");
  });

  it("renders modular sections when provided as children", () => {
    const html = renderToStaticMarkup(
      <ProfilePage username="alice" displayName="Alicja">
        <ProfileSection
          title="Ulubione ligi"
          description="Wybierz ligi, które chcesz mieć pod ręką."
        >
          siatka lig
        </ProfileSection>
      </ProfilePage>,
    );

    expect(html).toContain("Ulubione ligi");
    expect(html).toContain("Wybierz ligi, które chcesz mieć pod ręką.");
    expect(html).toContain("siatka lig");
  });
});

describe("ProfileSection", () => {
  it("renders a title without a description when none is given", () => {
    const html = renderToStaticMarkup(
      <ProfileSection title="Ustawienia">treść</ProfileSection>,
    );

    expect(html).toContain("Ustawienia");
    expect(html).toContain("treść");
  });
});
