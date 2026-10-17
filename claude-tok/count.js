// Token-count a manifest of files with Anthropic's Claude tokenizer.
const fs = require('fs');
const tokenizer = require('@anthropic-ai/tokenizer');

const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const [key, file] of Object.entries(manifest)) {
  const text = fs.readFileSync(file, 'utf8');
  out[key] = tokenizer.countTokens(text);
}
fs.writeFileSync(process.argv[3], JSON.stringify(out));
console.log('counted', Object.keys(out).length, 'files');
