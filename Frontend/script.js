const tracks = [
  {
    title: 'Midnight Switch',
    artist: 'Demo Artist',
    duration: '3:24',
  },
  {
    title: 'Sensor Groove',
    artist: 'Music Switcher',
    duration: '2:58',
  },
  {
    title: 'Frontend Flow',
    artist: 'Template Band',
    duration: '4:05',
  },
];

const trackTitle = document.querySelector('#track-title');
const trackArtist = document.querySelector('#track-artist');
const trackList = document.querySelector('#track-list');
const playButton = document.querySelector('#play-btn');
const nextButton = document.querySelector('#next-btn');
const previousButton = document.querySelector('#previous-btn');
const shuffleButton = document.querySelector('#shuffle-btn');
const progressFill = document.querySelector('#progress-fill');
const currentTime = document.querySelector('#current-time');
const duration = document.querySelector('#duration');
const volumeControl = document.querySelector('#volume-control');
const autoSwitch = document.querySelector('#auto-switch');

let currentTrackIndex = 0;
let isPlaying = false;
let progress = 0;
let progressTimer = null;

function renderPlaylist() {
  trackList.innerHTML = '';

  tracks.forEach((track, index) => {
    const listItem = document.createElement('li');
    const button = document.createElement('button');

    button.className = `track-item${index === currentTrackIndex ? ' active' : ''}`;
    button.type = 'button';
    button.innerHTML = `
      <span class="track-meta">
        <strong>${track.title}</strong>
        <span>${track.artist}</span>
      </span>
      <span class="track-duration">${track.duration}</span>
    `;

    button.addEventListener('click', () => {
      selectTrack(index);
      playTrack();
    });

    listItem.appendChild(button);
    trackList.appendChild(listItem);
  });
}

function selectTrack(index) {
  currentTrackIndex = index;
  progress = 0;

  const track = tracks[currentTrackIndex];
  trackTitle.textContent = track.title;
  trackArtist.textContent = track.artist;
  duration.textContent = track.duration;

  updateProgress();
  renderPlaylist();
}

function playTrack() {
  isPlaying = true;
  playButton.textContent = 'Pause';
  startProgressTimer();
}

function pauseTrack() {
  isPlaying = false;
  playButton.textContent = 'Play';
  stopProgressTimer();
}

function togglePlayback() {
  if (isPlaying) {
    pauseTrack();
  } else {
    playTrack();
  }
}

function nextTrack() {
  const nextIndex = (currentTrackIndex + 1) % tracks.length;
  selectTrack(nextIndex);

  if (isPlaying) {
    playTrack();
  }
}

function previousTrack() {
  const previousIndex = (currentTrackIndex - 1 + tracks.length) % tracks.length;
  selectTrack(previousIndex);

  if (isPlaying) {
    playTrack();
  }
}

function shuffleTracks() {
  const randomIndex = Math.floor(Math.random() * tracks.length);
  selectTrack(randomIndex);

  if (!isPlaying) {
    playTrack();
  }
}

function updateProgress() {
  progressFill.style.width = `${progress}%`;
  currentTime.textContent = `0:${String(Math.floor(progress / 2)).padStart(2, '0')}`;
}

function startProgressTimer() {
  stopProgressTimer();

  progressTimer = window.setInterval(() => {
    progress += 2;

    if (progress >= 100) {
      progress = 100;
      updateProgress();

      if (autoSwitch.checked) {
        nextTrack();
      } else {
        pauseTrack();
      }

      return;
    }

    updateProgress();
  }, 1000);
}

function stopProgressTimer() {
  if (progressTimer) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

playButton.addEventListener('click', togglePlayback);
nextButton.addEventListener('click', nextTrack);
previousButton.addEventListener('click', previousTrack);
shuffleButton.addEventListener('click', shuffleTracks);

volumeControl.addEventListener('input', (event) => {
  console.log(`Volume changed to ${event.target.value}%`);
});

selectTrack(currentTrackIndex);