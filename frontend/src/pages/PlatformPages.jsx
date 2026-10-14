import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChallengeCard, ChallengeDialog } from '../components/ChallengeCard.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import api from '../services/api.js';
import {
  prototypeChallenges,
  prototypeImpactStats,
  prototypeImpactTracking,
  prototypeActiveTeam,
  prototypeMilestones,
  prototypePendingTeam,
  prototypeReviewScores,
  prototypeReviewTotal,
  prototypeStats,
  prototypeSubmissionItems,
  prototypeTasks,
  prototypeTeamMembers,
} from '../data/prototypeData.js';

function SectionHeading({ title, description, action }) {
  return (
    <div className="section-title">
      <div><h2>{title}</h2>{description && <p className="muted">{description}</p>}</div>
      {action}
    </div>
  );
}

function StatCard({ label, value, detail, positive }) {
  return <article className="card stat"><div className="muted">{label}</div><div className="num">{value}</div><div className={positive ? 'match' : 'muted'}>{detail}</div></article>;
}

function Flow({ steps }) {
  return <div className="flow">{steps.map((step, index) => <div className="flow-step" key={step}>{step}{index < steps.length - 1 && <span className="arrow" aria-hidden="true">→</span>}</div>)}</div>;
}

export function Dashboard() {
  const featured = prototypeChallenges.slice(0, 3);
  const [selected, setSelected] = useState(null);

  return (
    <>
      <section className="hero">
        <div>
          <h2>Turn real problems into real solutions.</h2>
          <p>Connect societal challenges with students, universities and industry through one collaborative platform.</p>
          <span className="pill">SIH26043 · Smart Education · Software</span>
        </div>
        <span aria-hidden="true" className="hero-mark">◌</span>
      </section>
      <div className="grid g4 dashboard-stats">
        {prototypeStats.map((stat) => <StatCard key={stat.label} {...stat} />)}
      </div>
      <SectionHeading title="Recommended for you" action={<Link className="btn secondary" to="/challenges">Browse all</Link>} />
      <div className="grid g3">
        {featured.map((challenge) => <ChallengeCard challenge={challenge} key={challenge.title} onOpen={setSelected} />)}
      </div>
      <SectionHeading title="Challenge lifecycle" />
      <div className="card"><Flow steps={['Problem Owner · Post', 'AI Engine · Analyze', 'Students / Teams · Match', 'Collaboration · Build', 'Review · Evaluate', 'Impact · Deploy']} /></div>
      <ChallengeDialog challenge={selected} onClose={() => setSelected(null)} />
    </>
  );
}

export function ChallengeHub() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All categories');
  const [sort, setSort] = useState('AI match');
  const [selected, setSelected] = useState(null);
  const challenges = useMemo(() => {
    const filtered = prototypeChallenges.filter((challenge) => {
      const matchesQuery = `${challenge.title} ${challenge.category} ${challenge.location} ${challenge.skills.join(' ')}`.toLowerCase().includes(query.toLowerCase());
      return matchesQuery && (category === 'All categories' || challenge.category === category);
    });
    const sorted = [...filtered];
    if (sort === 'Newest') return sorted.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    if (sort === 'Impact') return sorted.sort((a, b) => b.impactScore - a.impactScore);
    return sorted.sort((a, b) => parseInt(b.match, 10) - parseInt(a.match, 10));
  }, [category, query, sort]);

  return (
    <>
      <SectionHeading title="Challenge Hub" description="Discover societal challenges and find the right opportunity." action={<Link className="btn primary" to="/owner">＋ Post challenge</Link>} />
      <div className="card filter-panel">
        <div className="grid g3">
          <input aria-label="Search challenges" className="form" onChange={(event) => setQuery(event.target.value)} placeholder="Search challenges..." value={query} />
          <select aria-label="Filter by category" onChange={(event) => setCategory(event.target.value)} value={category}>
            <option>All categories</option><option>AI / ML</option><option>Environment</option><option>Education</option><option>Healthcare</option><option>Smart City</option>
          </select>
          <select aria-label="Sort challenges" onChange={(event) => setSort(event.target.value)} value={sort}>
            <option value="AI match">Sort: AI match</option><option>Newest</option><option>Impact</option>
          </select>
        </div>
      </div>
      {challenges.length ? <div className="grid g3">{challenges.map((challenge) => <ChallengeCard challenge={challenge} key={challenge.title} onOpen={setSelected} />)}</div> : <div className="empty-state">No challenges match these filters.</div>}
      <ChallengeDialog challenge={selected} onClose={() => setSelected(null)} />
    </>
  );
}

export function Matching() {
  const [form, setForm] = useState({ title: '', description: '', expectedOutcome: '', requiredSkills: '' });
  const [analysis, setAnalysis] = useState(null);
  const [matches, setMatches] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  function payload() {
    return {
      title: form.title.trim(),
      description: form.description.trim(),
      expected_outcome: form.expectedOutcome.trim() || null,
      required_skills: form.requiredSkills.split(',').map((skill) => skill.trim()).filter(Boolean),
    };
  }

  async function analyze() {
    setBusy('analysis');
    setError('');
    setMatches(null);
    try {
      const { data } = await api.post('/api/matching/analyze', payload());
      setAnalysis(data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? 'Challenge analysis failed. Check the API connection and try again.');
    } finally {
      setBusy('');
    }
  }

  async function findMatches() {
    setBusy('matching');
    setError('');
    try {
      const { data } = await api.post('/api/matching/students', { ...payload(), limit: 20 });
      setAnalysis(data.challenge_analysis);
      setMatches(data.matches);
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? 'Student matching failed. Check the API and embedding model, then try again.');
    } finally {
      setBusy('');
    }
  }

  return (
    <>
      <SectionHeading title="AI Matching Engine" description="Analyze a challenge and compare it with registered student profiles." />
      <div className="grid g2">
        <form className="card form" onSubmit={(event) => { event.preventDefault(); void analyze(); }}>
          <span className="badge">Challenge input</span>
          <label>Challenge title<input maxLength="160" minLength="5" onChange={(event) => setForm({ ...form, title: event.target.value })} required value={form.title} /></label>
          <label>Description<textarea maxLength="10000" minLength="20" onChange={(event) => setForm({ ...form, description: event.target.value })} required rows="5" value={form.description} /></label>
          <label>Expected outcome<textarea maxLength="3000" onChange={(event) => setForm({ ...form, expectedOutcome: event.target.value })} rows="3" value={form.expectedOutcome} /></label>
          <label>Known required skills<input onChange={(event) => setForm({ ...form, requiredSkills: event.target.value })} placeholder="Python, GIS, IoT" value={form.requiredSkills} /></label>
          <div className="ai-actions">
            <button className="btn outline" disabled={Boolean(busy)} type="submit">{busy === 'analysis' ? 'Analyzing…' : 'Analyze challenge'}</button>
            <button className="btn primary" disabled={Boolean(busy) || form.title.trim().length < 5 || form.description.trim().length < 20} onClick={() => void findMatches()} type="button">{busy === 'matching' ? 'Matching students…' : 'Find student matches'}</button>
          </div>
          {error && <p className="auth-error" role="alert">{error}</p>}
        </form>

        <article aria-live="polite" className="card ai-analysis">
          <h2 className="card-title">Challenge analysis</h2>
          {analysis ? <>
            <div className="analysis-facts"><div><span className="muted">Category</span><b>{analysis.category}</b></div><div><span className="muted">Domain</span><b>{analysis.domain}</b></div><div><span className="muted">Difficulty</span><b>{analysis.difficulty}</b></div></div>
            <div className="matchbox"><b>Summary</b><p className="muted">{analysis.summary}</p></div>
            <div className="analysis-group"><b>Required skills</b><div className="tags spaced">{analysis.required_skills.length ? analysis.required_skills.map((skill) => <span className="tag" key={skill}>{skill}</span>) : <span className="muted">No skills detected yet.</span>}</div></div>
            <div className="analysis-group"><b>Keywords</b><div className="tags spaced">{analysis.keywords.map((keyword) => <span className="tag" key={keyword}>{keyword}</span>)}</div></div>
          </> : <div className="empty-state">Enter a challenge and analyze it to see its category, domain, skills, keywords, difficulty, and summary.</div>}
        </article>
      </div>
      {matches !== null && <section aria-live="polite" className="ai-matches top-space">
        <SectionHeading title="Student matches" description={`${matches.length} registered student${matches.length === 1 ? '' : 's'} ranked by challenge, skill, interest, and experience similarity.`} />
        {matches.length ? <div className="grid g2">{matches.map((match) => <article className="card match-result" key={match.student_id}>
          <div className="match-result-heading"><div><h3>{match.student_name}</h3><span className="muted">Domain similarity {match.domain_similarity}%</span></div><span className="match-percent">{match.match_percentage}%</span></div>
          <div aria-label={`Overall match ${match.match_percentage}%`} className="progress"><span style={{ width: `${match.match_percentage}%` }} /></div>
          <div className="analysis-group"><b>Matched skills</b><div className="tags spaced">{match.matched_skills.length ? match.matched_skills.map((skill) => <span className="tag skill-match" key={skill}>{skill}</span>) : <span className="muted">No direct skill matches</span>}</div></div>
          <div className="analysis-group"><b>Missing skills</b><div className="tags spaced">{match.missing_skills.length ? match.missing_skills.map((skill) => <span className="tag" key={skill}>{skill}</span>) : <span className="muted">No required skills missing</span>}</div></div>
          <p className="match-explanation">{match.explanation}</p>
        </article>)}</div> : <div className="empty-state">No active student profiles are available to match yet.</div>}
      </section>}
    </>
  );
}

export function Teams() {
  const [requested, setRequested] = useState(false);
  return (
    <>
      <SectionHeading title="My Teams" description="Teams formed around real-world challenges." action={<Link className="btn primary" to="/matching">Find teammates</Link>} />
      <div className="grid g2">
        <article className="card"><span className="badge green">Active</span><h3>{prototypeActiveTeam.name}</h3><p className="muted">Challenge: {prototypeActiveTeam.challengeTitle}</p>
          {prototypeTeamMembers.map((member) => <div className="person" key={member.name}><div className="personleft"><span className="mini">{member.initials}</span><div><b>{member.name}</b><div className="muted">{member.role}</div></div></div><span className="tag">{member.tag}</span></div>)}
          <p className="muted top-space">Project progress</p><div className="progress"><span style={{ width: `${prototypeActiveTeam.progress}%` }} /></div><div className="progress-label"><span>{prototypeActiveTeam.phase}</span><b>{prototypeActiveTeam.progress}%</b></div><Link className="btn primary top-space" to="/workspace">Open workspace</Link>
        </article>
        <article className="card"><span className="badge orange">Pending</span><h3>{prototypePendingTeam.challengeTitle}</h3><p className="muted">You have been recommended for this challenge.</p><div className="notice">AI recommends adding an {prototypePendingTeam.missingSkill} member to complete the skill mix.</div><button className="btn success top-space" onClick={() => setRequested(true)} type="button">{requested ? 'Request noted' : 'Request to join'}</button>{requested && <p className="form-message" role="status">Join requests will be sent when team services are connected. No request was sent.</p>}</article>
      </div>
    </>
  );
}

export function Workspace() {
  const [message, setMessage] = useState('');
  return (
    <>
      <SectionHeading title="Collaboration Workspace" description={`${prototypeActiveTeam.name} · ${prototypeActiveTeam.challengeTitle}`} action={<button className="btn primary" onClick={() => setMessage('Solution submission will be connected in a later phase. Nothing was submitted.')} type="button">Submit solution</button>} />
      <div className="grid g3">
        <article className="card"><h3 className="card-title">Milestones</h3><div className="timeline">{prototypeMilestones.map((milestone) => <div className="step" key={milestone.title}><span className="dot">{milestone.marker}</span><div><b>{milestone.title}</b><div className="muted">{milestone.status}</div></div></div>)}</div></article>
        <article className="card"><h3 className="card-title">Tasks</h3>{prototypeTasks.map((task) => <label className="task" key={task.title}><input defaultChecked={task.done} type="checkbox" />{task.title}</label>)}</article>
        <article className="card"><h3 className="card-title">Mentor feedback</h3><div className="notice">Industry mentor: “{prototypeActiveTeam.mentorFeedback}”</div><button className="btn outline top-space" onClick={() => setMessage('Discussion replies will be connected to the collaboration API in a later phase.')} type="button">Reply to mentor</button></article>
      </div>
      <article className="card top-space"><h3 className="card-title">Solution submission</h3><table className="table"><thead><tr><th>Deliverable</th><th>Status</th><th>Link</th></tr></thead><tbody>{prototypeSubmissionItems.map((item) => <tr key={item.name}><td>{item.name}</td><td><span className={`badge ${item.status === 'Draft' ? 'orange' : 'green'}`}>{item.status}</span></td><td>{item.status === 'Draft' ? 'Open' : 'View'}</td></tr>)}</tbody></table></article>
      {message && <p className="form-message" role="status">{message}</p>}
    </>
  );
}

export function Impact() {
  return (
    <>
      <SectionHeading title="Review & Impact Dashboard" description="Evaluate solutions and track real-world outcomes." />
      <div className="grid g4">{prototypeImpactStats.map((stat) => <StatCard key={stat.label} {...stat} />)}</div>
      <div className="grid g2 top-space">
        <article className="card"><h3 className="card-title">Solution review</h3><table className="table"><thead><tr><th>Criterion</th><th>Weight</th><th>Score</th></tr></thead><tbody>{prototypeReviewScores.map((item) => <tr key={item.criterion}><td>{item.criterion}</td><td>{item.weight}</td><td>{item.score}</td></tr>)}</tbody></table><div className="review-score">{prototypeReviewTotal}</div></article>
        <article className="card"><h3 className="card-title">Impact tracking</h3>{prototypeImpactTracking.map((item) => <div className="person" key={item.label}><div><b>{item.label}</b><div className="muted">{item.detail}</div></div><b>{item.value}</b></div>)}</article>
      </div>
    </>
  );
}

export function PostChallenge() {
  const [submitted, setSubmitted] = useState(false);
  function handleSubmit(event) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <>
      <SectionHeading title="Post a Societal Challenge" description="Citizens, government, NGOs and industry can submit real-world problems." />
      <div className="card">
        <form className="form" onSubmit={handleSubmit}>
          <label>Challenge title<input maxLength="120" name="title" placeholder="e.g. Smart Water Leakage Detection" required /></label>
          <label>Problem description<textarea maxLength="3000" name="description" placeholder="Describe the real-world problem, affected users and desired outcome..." required rows="5" /></label>
          <div className="grid g2"><label>Category<select defaultValue="Smart City" name="category"><option>Smart City</option><option>Environment</option><option>Education</option><option>Healthcare</option><option>AI / ML</option></select></label><label>Location<input maxLength="120" name="location" placeholder="City / State" required /></label></div>
          <label>Available data / resources<input maxLength="500" name="resources" placeholder="Dataset, APIs, sensors, reports, etc." /></label>
          <label>Expected outcome<textarea maxLength="1500" name="outcome" placeholder="What should the solution achieve?" rows="3" /></label>
          <div><button className="btn primary" type="submit">Submit challenge for AI analysis</button></div>
        </form>
        {submitted && <p className="form-message" role="status">The form is valid, but challenge submission and AI analysis are not connected until the API phases. Nothing was submitted.</p>}
        <div className="matchbox"><b>What happens next?</b><p className="muted">The platform will validate and analyze the submission, detect similar challenges, extract required skills and recommend relevant students / teams when those services are connected.</p></div>
      </div>
    </>
  );
}

const profileFieldsByRole = {
  student: [
    { key: 'college', label: 'College / institution' },
    { key: 'branch', label: 'Branch / course' },
    { key: 'year', label: 'Year of study', type: 'year' },
    { key: 'skills', label: 'Skills (comma-separated)', type: 'list' },
    { key: 'interests', label: 'Interests (comma-separated)', type: 'list' },
    { key: 'experience', label: 'Experience' },
    { key: 'github', label: 'GitHub URL', type: 'url' },
    { key: 'linkedin', label: 'LinkedIn URL', type: 'url' },
    { key: 'portfolio', label: 'Portfolio URL', type: 'url' },
  ],
  problem_owner: [
    { key: 'organization_name', label: 'Organization / owner name' },
    { key: 'organization_type', label: 'Organization type', type: 'organization' },
    { key: 'location', label: 'Location' },
  ],
  mentor: [
    { key: 'organization_name', label: 'Organization' },
    { key: 'expertise', label: 'Areas of expertise' },
    { key: 'skills', label: 'Skills (comma-separated)', type: 'list' },
  ],
  faculty: [
    { key: 'university', label: 'University / institution' },
    { key: 'department', label: 'Department' },
  ],
};

function profileInputValue(value, type) {
  if (type === 'list') return Array.isArray(value) ? value.join(', ') : '';
  return value ?? '';
}

export function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const [name, setName] = useState(user.name ?? '');
  const [profile, setProfile] = useState(() => Object.fromEntries(
    Object.entries(user.profile ?? {}).map(([key, value]) => [key, profileInputValue(value, ['skills', 'interests'].includes(key) ? 'list' : '')]),
  ));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const fields = profileFieldsByRole[user.role] ?? [];

  function updateField(event) {
    setProfile((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    const updatedProfile = {};
    fields.forEach(({ key, type }) => {
      const value = profile[key] ?? '';
      if (type === 'list') {
        updatedProfile[key] = value.split(',').map((item) => item.trim()).filter(Boolean);
      } else if (key === 'year') {
        updatedProfile[key] = value ? Number(value) : null;
      } else {
        updatedProfile[key] = value.trim() || null;
      }
    });

    try {
      await updateProfile({
        ...(name.trim() ? { name: name.trim() } : {}),
        profile: updatedProfile,
      });
      setNotice('Your profile has been updated.');
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Your profile could not be updated. Check the API connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <SectionHeading title="My Profile" description="Add or update your personal information whenever you are ready. These details are optional." />
      <form className="card form profile-form" onSubmit={handleSubmit}>
        <label>Full name<input autoComplete="name" maxLength="120" minLength="2" onChange={(event) => setName(event.target.value)} value={name} /></label>
        <label>Email address<input autoComplete="email" disabled type="email" value={user.email} /></label>
        {fields.map(({ key, label, type }) => (
          <label key={key}>{label}
            {type === 'year' ? (
              <select name={key} onChange={updateField} value={profile[key] ?? ''}>
                <option value="">Not specified</option>
                <option value="1">1st year</option><option value="2">2nd year</option><option value="3">3rd year</option>
                <option value="4">4th year</option><option value="5">5th year</option><option value="6">6th year</option>
                <option value="7">7th year</option><option value="8">8th year</option>
              </select>
            ) : type === 'organization' ? (
              <select name={key} onChange={updateField} value={profile[key] ?? ''}>
                <option value="">Not specified</option><option value="government">Government</option><option value="ngo">NGO</option>
                <option value="industry">Industry</option><option value="citizen">Citizen</option><option value="other">Other</option>
              </select>
            ) : (
              <input autoComplete={type === 'url' ? 'url' : undefined} name={key} onChange={updateField} type={type === 'url' ? 'url' : 'text'} value={profile[key] ?? ''} />
            )}
          </label>
        ))}
        {error && <p className="auth-error" role="alert">{error}</p>}
        {notice && <p className="auth-notice" role="status">{notice}</p>}
        <button className="btn primary" disabled={busy} type="submit">{busy ? 'Saving…' : 'Save profile'}</button>
      </form>
    </>
  );
}