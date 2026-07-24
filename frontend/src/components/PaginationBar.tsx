import Link from "next/link";

interface PaginationBarProps {
  basePath: string;
  currentPage: number;
  totalCount: number;
  pageSize: number;
  searchParams: Record<string, string | undefined>;
}

export function PaginationBar({
  basePath,
  currentPage,
  totalCount,
  pageSize,
  searchParams,
}: PaginationBarProps) {
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  if (totalPages <= 1) {
    return null;
  }

  function buildHref(page: number): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(searchParams)) {
      if (value && key !== "page") {
        params.set(key, value);
      }
    }
    if (page > 1) {
      params.set("page", String(page));
    }
    const query = params.toString();
    return query ? `${basePath}?${query}` : basePath;
  }

  return (
    <div className="flex items-center justify-between gap-4 text-sm text-slate-300">
      <p>
        Strona {currentPage} z {totalPages} ({totalCount} wyników)
      </p>
      <div className="flex gap-2">
        {currentPage > 1 ? (
          <Link
            href={buildHref(currentPage - 1)}
            className="rounded-lg border border-slate-600 px-3 py-1.5 transition hover:bg-slate-800"
          >
            Poprzednia
          </Link>
        ) : null}
        {currentPage < totalPages ? (
          <Link
            href={buildHref(currentPage + 1)}
            className="rounded-lg border border-slate-600 px-3 py-1.5 transition hover:bg-slate-800"
          >
            Następna
          </Link>
        ) : null}
      </div>
    </div>
  );
}
