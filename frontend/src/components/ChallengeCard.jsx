import React, { useState } from 'react';

export function ChallengeCard({ challenge, onOpen }) {
  return (
    <article className="card challenge">
      <span className={`badge ${challenge.tone ?? ''}`}>{challenge.category}</span>
      <h3>{challenge.title}</h3>
      <p className="muted">{challenge.location} · {challenge.owner}</p>
      <div className="tags">
        {challenge.skills.map((skill) => <span className="tag" key={skill}>{skill}</span>)}
      </div>
      <div className="match">AI Match {challenge.match}</div>
      <div className="progress" aria-label={`Match score ${challenge.match}`}>
        <span style={{ width: challenge.match }} />
      </div>
      <button className="btn primary" onClick={() => onOpen(challenge)} type="button">View & match</button>
    </article>
  );
}

export function ChallengeDialog({ challenge, onClose }) {
  const [message, setMessage] = useState('');

  if (!challenge) return null;

  return (
    <div className="modal open" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section aria-labelledby="challenge-dialog-title" aria-modal="true" className="modalbox" role="dialog">
        <div className="modalhead">
          <h2 id="challenge-dialog-title">{challenge.title}</h2>
          <button aria-label="Close challenge details" className="close" onClick={onClose} type="button">×</button>
        </div>
        <div className="matchbox">
          <div className="match">AI Match {challenge.match}</div>
          <div className="progress"><span style={{ width: challenge.match }} /></div>
        </div>
        <h3>Problem</h3>
        <p className="muted">{challenge.description}</p>
        <h3>Required skills</h3>
        <div className="tags">{challenge.skills.map((skill) => <span className="tag" key={skill}>{skill}</span>)}</div>
        <h3>Expected outcome</h3>
        <p className="muted">Prototype, documentation and a measurable impact plan.</p>
        <button className="btn primary full-width" onClick={() => setMessage('Applications will be connected to the platform API in a later phase. No application was submitted.')} type="button">
          Apply / Join Challenge
        </button>
        {message && <p className="form-message" role="status">{message}</p>}
      </section>
    </div>
  );
}