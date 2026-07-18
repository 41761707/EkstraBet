import type { ReactNode } from "react";
import { ExpandableSection } from "@/components/ExpandableSection";

interface HomeSectionProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  id?: string;
}

export function HomeSection(props: HomeSectionProps) {
  return <ExpandableSection {...props} />;
}
