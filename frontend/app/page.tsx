"use client";

import { useState } from "react";
import JobForm from "@/components/JobForm";
import ResultsView from "@/components/ResultsView";
import { ApiError, createJob } from "@/lib/api";
import type { JobRequest, JobResponse } from "@/lib/types";

export default function HomePage() {
  const [result, setResult] = useState<JobResponse | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(req: JobRequest) {
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      setResult(await createJob(req));
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <JobForm onSubmit={handleSubmit} submitting={submitting} />

      {submitting && (
        <p>Working&hellip;</p>
      )}

      {error && <ErrorReport error={error} />}

      {result && (
        <>
          <hr />
          <ResultsView result={result} />
        </>
      )}
    </div>
  );
}

const KIND_HEADING: Record<string, string> = {
  invalid_input: "Check the query",
  not_found: "Not found",
  upstream: "An external database is unavailable",
  missing_dependency: "A required tool is missing",
  pipeline: "The pipeline could not finish",
  internal: "Unexpected error",
};

function ErrorReport({ error }: { error: ApiError | Error }) {
  const api = error instanceof ApiError ? error : null;
  const heading = api ? KIND_HEADING[api.kind] ?? "Error" : "Error";

  return (
    <div role="alert">
      <h3>{heading}</h3>
      <p>{error.message}</p>
      {api?.hint && <p className="meta">{api.hint}</p>}
      {api && (api.stage || api.status > 0) && (
        <p className="meta">
          {api.stage && (
            <>
              Failed at the <b>{api.stage}</b> stage.{" "}
            </>
          )}
          {api.status > 0 && <>HTTP {api.status}.</>}
        </p>
      )}
    </div>
  );
}
