const API_URL = 'http://127.0.0.1:8000';
const playButton = document.querySelector('#play-btn');
const volumeControl = document.querySelector('#volume-control');
const playlistNameInput = document.querySelector('#playlist-name');
const connectionStatus = document.querySelector('#connection-status');

let isPlaying = false;

function setConnectionStatus(message, state = '') {
  connectionStatus.textContent = message;
  connectionStatus.className = `connection-status${state ? ` is-${state}` : ''}`;
}

async function requestApi(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.error || 'The backend could not complete the request.');
  }

  return result;
}

async function playMusic() {
  const playlist = playlistNameInput.value.trim();

  if (!playlist) {
    setConnectionStatus('Enter an Apple Music playlist name before playing.', 'error');
    playlistNameInput.focus();
    return;
  }

  playButton.disabled = true;
  setConnectionStatus('Starting Music Switcher…');

  try {
    await requestApi('/api/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist }),
    });

    isPlaying = true;
    playButton.textContent = 'Pause';
    setConnectionStatus(`Started with “${playlist}”. Switch to another tab or app to begin playback.`, 'success');
  } catch (error) {
    setConnectionStatus(
      `Could not start playback: ${error.message}`,
      'error',
    );
  } finally {
    playButton.disabled = false;
  }
}

async function pauseMusic() {
  playButton.disabled = true;
  setConnectionStatus('Stopping Music Switcher…');

  try {
    await requestApi('/api/stop', { method: 'POST' });
    isPlaying = false;
    playButton.textContent = 'Play';
    setConnectionStatus('Music Switcher is stopped.', 'success');
  } catch (error) {
    setConnectionStatus(`Could not stop the backend. (${error.message})`, 'error');
  } finally {
    playButton.disabled = false;
  }
}

function togglePlayback() {
  if (isPlaying) {
    pauseMusic();
  } else {
    playMusic();
  }
}

playButton.addEventListener('click', togglePlayback);

volumeControl.addEventListener('input', (event) => {
  console.log(`Volume changed to ${event.target.value}%`);
});

async function checkBackendStatus() {
  try {
    const { running } = await requestApi('/api/status');
    isPlaying = running;
    playButton.textContent = running ? 'Pause' : 'Play';
    setConnectionStatus(
      running ? 'Music Switcher backend is currently playing.' : 'Music Switcher backend is ready.',
      'success',
    );
  } catch (error) {
    setConnectionStatus('Backend is offline. Run Backend/api_server.py to connect it.', 'error');
  }
}

checkBackendStatus();