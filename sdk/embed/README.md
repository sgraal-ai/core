# Sgraal Embed SDK

Zero-config memory governance for any web app — single `<script>` tag.

## Usage

```html
<script src="https://api.sgraal.com/v1/embed/sgraal-embed.js"
        data-api-key="sg_demo_playground"
        data-domain="general"
        data-block-on="BLOCK,WARN">
</script>
```

## API

```javascript
// Manual preflight
const result = await window.sgraal.preflight([
  { id: "m1", content: "...", type: "semantic", timestamp_age_days: 5,
    source_trust: 0.9, source_conflict: 0.05, downstream_count: 1 }
]);

// Event listeners
window.sgraal.on('block', (data) => {
  console.log('Blocked:', data.recommended_action);
});

window.sgraal.on('warn', (data) => {
  console.log('Warning:', data.omega_mem_final);
});
```
