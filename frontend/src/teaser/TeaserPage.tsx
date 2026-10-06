
import { ERROR_MESSAGES } from "./labels";
import { TeaserEditor } from "./TeaserEditor";
import type { TeaserApi } from "./api";
import { useDeckDraft } from "./useDeckDraft";

interface Props {
  deckId: number | null;
  api?: TeaserApi;
  declarationHref?: string;
}

export function TeaserPage({ deckId, api, }: Props) {
  const { data, error, timedOut, refetch, isPolling } = useDeckDraft(deckId, api ? { fetchDraft: api.getDraft } : {});

  if (deckId === null) return null;
  if (error) {
    return (
      <div role="alert">
        <p>We could not load the processing status.</p>
        <button type="button" onClick={refetch}>Try again</button>
      </div>
    );
  }
  if (timedOut) {
    return (
      <div role="status">
        <p>Processing is taking longer than usual. You can leave this page and come back later.</p>
        <button type="button" onClick={refetch}>Check again</button>
      </div>
    );
  }
  if (data?.state === "FAILED") {
    return <p role="alert" className="tz-error">{ERROR_MESSAGES[data.error_code ?? "unexpected"]}</p>;
  }
  if (data?.state === "DRAFT_READY") {
    return <TeaserEditor deckId={deckId} draft={data} api={api} />;
  }
  return (
    <p role="status" aria-busy={isPolling}>
      {data?.state === "PROCESSING" ? "The AI is analysing your deck…" : "Your deck is queued for analysis…"}
      {" "}This usually takes less than a minute.
    </p>
  );
}