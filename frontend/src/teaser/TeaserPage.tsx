
import { ERROR_MESSAGES } from "./labels";
import { TeaserEditor } from "./TeaserEditor";
import { useDeckDraft } from "./useDeckDraft";
import { teaserApi } from "./api";


type Props = { deckId: number; onApproved?: () => void | Promise<void> };

export function TeaserPage({ deckId, onApproved }: Props) {
  const { data, error, timedOut, refetch, isPolling } = useDeckDraft(deckId, {
    fetchDraft: teaserApi.getDraft,
  });

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
    return <TeaserEditor deckId={deckId} draft={data} api={teaserApi} onApproved={onApproved} />;
  }
  return (
    <p role="status" aria-busy={isPolling}>
      {data?.state === "PROCESSING" ? "The AI is analysing your deck…" : "Your deck is queued for analysis…"}
      {" "}This usually takes less than a minute.
    </p>
  );
}