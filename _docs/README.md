# PaxD Documentation Site

This directory contains the GitHub Pages site for PaxD - a modern Python package manager for Windows.

## Structure

- `index.html` - Main page with hero, features, installation, packages, and docs
- `style.css` - Modern CSS with responsive design and animations
- `script.js` - Interactive functionality and mobile navigation

## GitHub Pages Setup

This site is designed to work with GitHub Pages using the `_docs` folder as the source.

To enable GitHub Pages:
1. Go to repository Settings
2. Navigate to Pages section
3. Set Source to "Deploy from a branch"
4. Select "main" branch and "/_docs" folder
5. Save settings

The site will be available at: `https://mralfiem591.github.io/paxd/`

## Local Development

To view locally:
1. Open `index.html` in a web browser
2. Or serve with a local HTTP server:
   ```bash
   cd _docs
   python -m http.server 8000
   ```
3. Visit `http://localhost:8000`

## Customization

- Update colors in CSS variables at the top of `style.css`
- Modify content in `index.html`
- Add new sections following the existing pattern
- Update links to point to your specific repository structure

## Dependencies

- Inter font from Google Fonts
- Prism.js for syntax highlighting
- Pure CSS and vanilla JavaScript (no frameworks)

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile responsive
- Progressive enhancement for older browsers
