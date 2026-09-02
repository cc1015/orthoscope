export default function JobPage({ params }: { params: { id: string } }) {
  return (
    <div>
      <h2>Job <span className="mono">{params.id}</span></h2>
      <p>
        Async job pages arrive once the backend exposes job state. For now the
        synchronous query renders its results on the <a href="/">index</a>.
      </p>
    </div>
  );
}
