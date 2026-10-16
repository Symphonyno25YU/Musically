# Frontend

This folder contains the frontend files for the Music Switcher web interface. The frontend is the part of the project that users see and interact with in the browser.

## File Descriptions

### `index.html`

The main webpage file. It defines the structure of the Music Switcher interface, including the header, navigation links, music player card, playlist area, and settings section.

This file also connects the page to:

- `styles.css` for visual design
- `script.js` for interactive behavior

### `styles.css`

The design and styling file. It controls how the website looks, including colors, spacing, layout, buttons, cards, the progress bar, and responsive behavior for smaller screens.

### `script.js`

The JavaScript logic file. It controls the interactive parts of the music player, including selecting tracks, play and pause behavior, next and previous buttons, shuffle, progress updates, volume input handling, and auto-switching to the next track.

## How the Files Work Together

- `index.html` creates the page structure.
- `styles.css` makes the page look polished and organized.
- `script.js` makes the page respond when the user clicks buttons or changes settings.

In simple terms:

| File | Purpose |
| --- | --- |
| `index.html` | Website structure and content |
| `styles.css` | Website design and layout |
| `script.js` | Website logic and behavior |

## Running the Frontend

From the project root, start the frontend and backend together:

```sh
cd /Users/symphonyno25/Desktop/Music_switcher
python3 start_music_switcher.py
```

Open `http://127.0.0.1:5500` in a web browser. The frontend calls the local
backend API at `http://127.0.0.1:8000` when you click **Play** or **Pause**.