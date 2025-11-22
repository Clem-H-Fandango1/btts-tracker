/*
 * Front-end logic for the public BTTS match viewer.  This script
 * fetches current match assignments from the server, displays a
 * score card for each participant and updates scores periodically.
 */

// How often to refresh the match scores (in milliseconds)
const REFRESH_INTERVAL_MS = 30000;

// Cached assignments mapping friend name -> eventId (or null)
let assignments = {};
// Cached group assignments mapping friend name -> "top" or "bottom"
let groups = {};

// Cached settings (title and message)
let settings = { title: '', message: '' };

// Flag indicating whether a sixer bet is active (any group is 'sixer')
let sixerActive = false;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  fetchData();
  // Periodically update scores
  setInterval(updateAllScores, REFRESH_INTERVAL_MS);
});

/**
 * Fetch the current assignments from the server and build the scorecards.
 */
async function fetchData() {
  try {
    const [assignRes, groupRes, settingsRes] = await Promise.all([
      fetch('/api/assignments'),
      fetch('/api/groups'),
      fetch('/api/settings'),
    ]);
    assignments = await assignRes.json();
    groups = await groupRes.json();
    settings = await settingsRes.json();
    // Update the page title based on settings.  If the title is blank, fall back
    // to a default of "BTTS Tracker".
    const titleElem = document.getElementById('app-title');
    if (titleElem) {
      const newTitle = (settings && settings.title && settings.title.trim()) ? settings.title : 'BTTS Tracker';
      titleElem.textContent = newTitle;
    }
    // Update the message bar based on settings.  If blank, hide the bar.
    const msgBar = document.getElementById('message-hero');
    if (msgBar) {
      const msg = (settings && settings.message && settings.message.trim()) ? settings.message : '';
      msgBar.textContent = msg;
      msgBar.style.display = msg ? 'block' : 'none';
    }
    // Determine if sixer bet is active (any group value is 'sixer')
    sixerActive = false;
    if (groups && Object.keys(groups).length > 0) {
      sixerActive = Object.values(groups).some((g) => g === 'sixer');
    }
    createScoreCards();
    // Immediately update scores once cards are created
    updateAllScores();
  } catch (err) {
    console.error('Failed to load assignments or groups', err);
  }
}

/**
 * Create a score card for each friend.  Initially displays a
 * placeholder if no match is assigned.
 */
function createScoreCards() {
  const topContainer = document.getElementById('top-cards');
  const bottomContainer = document.getElementById('bottom-cards');
  const sixerContainer = document.getElementById('sixer-cards');
  const topSection = document.getElementById('top-section');
  const bottomSection = document.getElementById('bottom-section');
  const sixerSection = document.getElementById('sixer-section');
  if (!topContainer || !bottomContainer || !sixerContainer) return;
  // Clear all containers
  topContainer.innerHTML = '';
  bottomContainer.innerHTML = '';
  sixerContainer.innerHTML = '';
  // Decide which sections to show/hide based on sixerActive
  if (sixerActive) {
    // Hide top and bottom sections and show sixer section
    if (topSection) topSection.style.display = 'none';
    if (bottomSection) bottomSection.style.display = 'none';
    if (sixerSection) sixerSection.style.display = 'block';
  } else {
    // Show top and bottom sections and hide sixer section
    if (topSection) topSection.style.display = 'block';
    if (bottomSection) bottomSection.style.display = 'block';
    if (sixerSection) sixerSection.style.display = 'none';
  }
  // Use the keys from assignments as friend names
  Object.keys(assignments).forEach((name) => {
    const card = document.createElement('div');
    card.className = 'score-card';
    card.id = `card-${name}`;
    // Friend name displayed in its own box above match info
    const friendBox = document.createElement('div');
    friendBox.className = 'friend-box';
    friendBox.textContent = name;
    card.appendChild(friendBox);
    // Create containers for match rows.  Each match has two rows: one for the
    // home team and one for the away team, with names and scores aligned.
    const matchInfo = document.createElement('div');
    matchInfo.className = 'match-info';
    // Home row
    const homeRow = document.createElement('div');
    homeRow.className = 'match-row';
    const homeNameSpan = document.createElement('span');
    homeNameSpan.className = 'team-name';
    homeRow.appendChild(homeNameSpan);
    const homeCardsSpan = document.createElement('span');
    homeCardsSpan.className = 'red-cards';
    homeRow.appendChild(homeCardsSpan);
    const homeScoreSpan = document.createElement('span');
    homeScoreSpan.className = 'team-score';
    homeRow.appendChild(homeScoreSpan);
    // Away row
    const awayRow = document.createElement('div');
    awayRow.className = 'match-row';
    const awayNameSpan = document.createElement('span');
    awayNameSpan.className = 'team-name';
    awayRow.appendChild(awayNameSpan);
    const awayCardsSpan = document.createElement('span');
    awayCardsSpan.className = 'red-cards';
    awayRow.appendChild(awayCardsSpan);
    const awayScoreSpan = document.createElement('span');
    awayScoreSpan.className = 'team-score';
    awayRow.appendChild(awayScoreSpan);
    matchInfo.appendChild(homeRow);
    matchInfo.appendChild(awayRow);
    card.appendChild(matchInfo);
    // Status and BTTS spans below match info
    const statusSpan = document.createElement('span');
    statusSpan.className = 'status';
    card.appendChild(statusSpan);
    const bttsSpan = document.createElement('span');
    bttsSpan.className = 'btts';
    card.appendChild(bttsSpan);
    // Attach references for updates later
    card.homeNameSpan = homeNameSpan;
    card.homeScoreSpan = homeScoreSpan;
    card.homeCardsSpan = homeCardsSpan;
    card.awayNameSpan = awayNameSpan;
    card.awayScoreSpan = awayScoreSpan;
    card.awayCardsSpan = awayCardsSpan;
    card.statusSpan = statusSpan;
    card.bttsSpan = bttsSpan;
    // Track BTTS state on the card (string 'true' or 'false') to avoid unnecessary class changes
    card.dataset.btts = 'false';
    // Append to appropriate container based on sixerActive and group
    if (sixerActive) {
      sixerContainer.appendChild(card);
    } else {
      const grp = groups[name] || 'bottom';
      if (grp === 'top') {
        topContainer.appendChild(card);
      } else {
        bottomContainer.appendChild(card);
      }
    }
  });
}

/**
 * Update the score for each assigned match card.
 */
function updateAllScores() {
  const names = Object.keys(assignments);
  names.forEach((name) => {
    const eventId = assignments[name];
    updateScoreCard(name, eventId);
  });
}

/**
 * Update the card for a single friend.
 *
 * @param {string} name Friend's nickname
 * @param {number} index Index of the card
 * @param {string|null} eventId Assigned event ID or null
 */
async function updateScoreCard(name, eventId) {
  const card = document.getElementById(`card-${name}`);
  if (!card) return;
  // Do not reset the entire class name.  We'll update the BTTS class only if necessary
  if (!eventId) {
    // No match assigned: clear dynamic spans without adding placeholder text
    card.homeNameSpan.textContent = '';
    card.homeScoreSpan.textContent = '';
    card.awayNameSpan.textContent = '';
    card.awayScoreSpan.textContent = '';
    card.statusSpan.textContent = '';
    card.bttsSpan.textContent = '';
    // Ensure BTTS styling is removed
    if (card.dataset.btts === 'true') {
      card.classList.remove('btts-hit');
      card.dataset.btts = 'false';
    }
    return;
  }
  try {
    const res = await fetch(`/api/match/${eventId}`);
    const data = await res.json();
    if (data.error) {
      card.homeNameSpan.textContent = '';
      card.homeScoreSpan.textContent = '';
      card.awayNameSpan.textContent = '';
      card.awayScoreSpan.textContent = '';
      card.statusSpan.textContent = 'Match data unavailable';
      card.bttsSpan.textContent = '';
      // Ensure BTTS styling is removed on error
      if (card.dataset.btts === 'true') {
        card.classList.remove('btts-hit');
        card.dataset.btts = 'false';
      }
      return;
    }
    const { homeTeam, awayTeam, homeScore, awayScore, status, kickoffTime, state, btts, homeRedCards = 0, awayRedCards = 0 } = data;
    // Apply or remove BTTS styling only if state has changed
    const prevBtts = card.dataset.btts === 'true';
    if (btts && !prevBtts) {
      card.classList.add('btts-just-hit');
      setTimeout(() => card.classList.remove('btts-just-hit'), 1200);
      // Add btts-hit class
      card.classList.add('btts-hit');
      card.dataset.btts = 'true';
    } else if (!btts && prevBtts) {
      // Remove btts-hit class
      card.classList.remove('btts-hit');
      card.dataset.btts = 'false';
    }
    // Match title
    // Update names and scores aligned on separate rows
    card.homeNameSpan.textContent = homeTeam;
    card.homeScoreSpan.textContent = homeScore;
    card.awayNameSpan.textContent = awayTeam;
    card.awayScoreSpan.textContent = awayScore;
    const rcIcon = '🟥';
    function formatRC(n){ if(!n||n<=0) return ''; if(n===1) return rcIcon; return rcIcon + ' x' + n; }
    card.homeCardsSpan.textContent = formatRC(homeRedCards);
    card.awayCardsSpan.textContent = formatRC(awayRedCards);
    // Kickoff time and status/minutes
    if (state === 'pre') {
      // Scheduled: show day and time (kickoffTime)
      card.statusSpan.textContent = kickoffTime;
    } else {
      // In progress or finished: show status (minutes, HT, FT, etc.)
      card.statusSpan.textContent = status;
    }
    // BTTS indicator
    card.bttsSpan.textContent = btts ? 'BTTS ✅' : '';
  } catch (err) {
    console.error('Failed to fetch match details', err);
    card.homeNameSpan.textContent = '';
    card.homeScoreSpan.textContent = '';
    card.awayNameSpan.textContent = '';
    card.awayScoreSpan.textContent = '';
    card.statusSpan.textContent = 'Error fetching match data';
    card.bttsSpan.textContent = '';
    // Ensure BTTS styling is removed on error
    if (card.dataset.btts === 'true') {
      card.classList.remove('btts-hit');
      card.dataset.btts = 'false';
    }
  }
}