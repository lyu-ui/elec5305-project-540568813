/* Local comparison playback. Selected files never leave the browser. */
const fileNames = {
  'Original_segment.wav': 'audio-original',
  'Noisy.wav': 'audio-noisy',
  'Estimated_Wiener.wav': 'audio-estimated',
  'Oracle_Wiener.wav': 'audio-oracle'
};
const objectUrls = new Map();
const input = document.getElementById('comparison-files');
const status = document.getElementById('comparison-status');
input.addEventListener('change', () => {
  for (const url of objectUrls.values()) URL.revokeObjectURL(url);
  objectUrls.clear();
  for (const id of Object.values(fileNames)) {
    const player = document.getElementById(id);
    player.pause();
    player.removeAttribute('src');
    player.load();
  }
  for (const file of input.files) {
    const id = fileNames[file.name];
    if (!id) continue;
    const url = URL.createObjectURL(file);
    objectUrls.set(id, url);
    document.getElementById(id).src = url;
  }
  const missing = Object.entries(fileNames).filter(([,id]) => !objectUrls.has(id)).map(([name]) => name);
  status.textContent = missing.length
    ? `${objectUrls.size}/4 files ready. Missing: ${missing.join(', ')}`
    : 'All four files are ready. Files stay on your device; use the same playback volume.';
});
document.querySelectorAll('audio').forEach(player => {
  player.addEventListener('play', () => {
    document.querySelectorAll('audio').forEach(other => {
      if (other !== player) other.pause();
    });
  });
});
