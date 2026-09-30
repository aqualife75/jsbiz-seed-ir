/** Pure, content-aware composition contract. No company content or runtime paths. */
export const VISUAL_VARIANTS = Object.freeze([
  'evidence_focus', 'comparison_focus', 'product_hero', 'market_layers',
  'timeline_focus', 'team_focus', 'cover_focus',
]);

/** Native quantitative axis with 4–6 legible intervals and label headroom. */
export function readableValueAxis(values) {
  const maxValue = Math.max(...values);
  if (!Number.isFinite(maxValue) || maxValue <= 0 || values.some(v => v < 0)) return {};
  const rough = maxValue / 4, power = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map(n => n * power).find(n => n >= rough) ?? power * 10;
  let max = Math.ceil(maxValue / step) * step;
  if ((max - maxValue) / maxValue < .10) max += step;
  const decimals = Math.max(0, -Math.floor(Math.log10(step))) + (Number.isInteger(step * 10 ** Math.max(0, -Math.floor(Math.log10(step)))) ? 0 : 1);
  // Use fixed decimals: optional '#' decimals can be read as SI formatting by
  // some native chart renderers (for example 0.5 appearing as 500m).
  return { min: 0, max, majorUnit: step, numberFormatCode: '#,##0' + (decimals ? '.' + '0'.repeat(Math.min(6, decimals)) : '') };
}

const descriptiveSize = b => String(b.text ?? b.detail ?? b.caption ?? '').length;
function supportWeights(blocks) {
  return blocks.map(b => b.type === 'image' ? 2.5 : b.type === 'metric' ? 1.5 :
    ['table', 'chart', 'steps', 'team', 'roadmap', 'mapping', 'formula'].includes(b.type) ? 3 :
    1 + Math.min(descriptiveSize(b) / 100, 1.2) + (b.disclosure ? .5 : 0));
}

/** Return null for legacy drafts: legacy layout semantics stay available. */
export function planVisualComposition(slide, blocks, config = {}) {
  const brief = slide.visual_brief;
  if (!brief) return null;
  const fail = message => { throw new Error(`${slide.id}: visual_brief ${message}`); };
  if (!VISUAL_VARIANTS.includes(brief.layout_variant)) fail('has an unknown layout_variant');
  const ids = blocks.map(b => b.id), order = brief.reading_order;
  if (!Array.isArray(order) || new Set(ids).size !== ids.length || new Set(order).size !== ids.length || order.length !== ids.length || ids.some(id => !order.includes(id)) || order.some(id => !ids.includes(id)))
    fail('reading_order must include every block ID exactly once');
  const primary = blocks.find(b => b.id === brief.primary_block_id);
  if (!primary) fail('primary_block_id must identify an existing block');
  const other = order.filter(id => id !== primary.id).map(id => blocks.find(b => b.id === id));
  const variant = brief.layout_variant;
  if (variant === 'product_hero' && !(primary.type === 'image' || primary.type === 'steps' && primary.items?.some(it => it.asset?.path)))
    fail('product_hero needs a primary source image or steps with an image asset');
  const compatible = { comparison_focus: ['table', 'mapping'], market_layers: ['formula'], timeline_focus: ['roadmap', 'steps'], team_focus: ['team'] };
  if (compatible[variant] && !compatible[variant].includes(primary.type)) fail(`${variant} has an incompatible primary block type`);
  const width = config.width_px ?? 1280, margin = config.margin_px ?? 72;
  const gutter = config.gutter_px ?? 28, top = config.body_top_px ?? (slide.subtitle ? 250 : 224);
  const bottom = config.body_bottom_px ?? 650, height = bottom - top, contentWidth = width - 2 * margin;
  const placements = [];
  const add = (b, x, y, w, h, role, extra = {}) => placements.push({ block_id: b.id, x, y, w, h, role, ...extra });
  const stack = (list, x, y, w, h, focusFirst = false) => {
    const weights = supportWeights(list), total = weights.reduce((a, b) => a + b, 0);
    let currentY = y;
    list.forEach((b, i) => {
      const bh = (h - gutter * (list.length - 1)) * weights[i] / total;
      add(b, x, currentY, w, bh, 'support', { surface: focusFirst && i === 0 && b.type === 'text' ? 'contrast' : 'open' });
      currentY += bh + gutter;
    });
  };
  const fullWithBand = (primaryStyle, bandHeight = 112) => {
    const ph = other.length ? height - bandHeight - gutter : height;
    add(primary, margin, top, contentWidth, ph, 'primary', primaryStyle);
    const available = contentWidth - gutter * (other.length - 1);
    const weights = supportWeights(other), total = weights.reduce((a, b) => a + b, 0);
    let x = margin;
    other.forEach((b, i) => {
      const w = available * weights[i] / total;
      add(b, x, top + ph + gutter, w, bandHeight, 'support', { compact: true, surface: 'open' });
      x += w + gutter;
    });
  };
  const split = (fraction, style = {}, contrast = false) => {
    if (!other.length) { add(primary, margin, top, contentWidth, height, 'primary', style); return; }
    const mainWidth = (contentWidth - gutter) * fraction;
    add(primary, margin, top, mainWidth, height, 'primary', style);
    stack(other, margin + mainWidth + gutter, top, contentWidth - mainWidth - gutter, height, contrast);
  };

  if (variant === 'product_hero') {
    if (primary.type === 'steps') fullWithBand({ semantic_style: 'featured_sequence', surface: 'open' }, 100);
    else {
      const aspect = config.block_image_aspects?.[primary.id];
      const portrait = Number.isFinite(aspect) && aspect < .9;
      split(portrait ? .38 : .61, { surface: 'paper', semantic_style: portrait ? 'portrait_product_image' : 'product_image', ...(aspect ? { image_aspect: aspect } : {}) }, true);
    }
  } else if (variant === 'comparison_focus') {
    // A wide matrix needs the full canvas; a short comparison retains a visible judgment column.
    if (primary.type === 'table' && primary.columns.length >= 4 || other.length > 2)
      fullWithBand({ semantic_style: 'comparison', surface: 'open' }, 104);
    else split(.73, { semantic_style: 'comparison', surface: 'open' }, true);
  } else if (variant === 'market_layers') {
    split(.73, { semantic_style: 'market_layers', surface: 'open' });
  } else if (variant === 'timeline_focus') {
    fullWithBand({ semantic_style: 'execution_timeline', surface: 'open' }, 96);
  } else if (variant === 'team_focus') {
    if (other.length === 1 && primary.items.length <= 3) split(.74, { semantic_style: 'team_roles', surface: 'open' }, true);
    else fullWithBand({ semantic_style: 'team_roles', surface: 'open' }, 108);
  } else if (variant === 'cover_focus') {
    const visual = primary.type === 'image' ? primary : other.find(b => b.type === 'image');
    if (visual) {
      const imageWidth = contentWidth * .46, leftWidth = contentWidth - imageWidth - gutter * 2;
      add(visual, margin + contentWidth - imageWidth, top, imageWidth, height, visual === primary ? 'primary' : 'hero_image', { surface: 'open', semantic_style: 'cover_image', image_aspect: config.block_image_aspects?.[visual.id] });
      if (visual === primary) stack(other, margin, top + 12, leftWidth, height - 24, false);
      else {
        const remaining = other.filter(b => b !== visual), primaryH = remaining.length ? height * .55 : height;
        add(primary, margin, top, leftWidth, primaryH, 'primary', { surface: 'open', semantic_style: 'cover_statement' });
        stack(remaining, margin, top + primaryH + gutter, leftWidth, height - primaryH - gutter, false);
      }
    } else split(.61, { semantic_style: 'cover_statement', surface: 'open' });
  } else {
    if (['steps', 'mapping', 'roadmap', 'team'].includes(primary.type)) fullWithBand({ semantic_style: 'editorial_sequence', surface: 'open' }, 108);
    else split(primary.type === 'text' ? .60 : .67, { semantic_style: 'evidence', surface: primary.type === 'metric' ? 'contrast' : 'open' });
  }
  if (placements.some(p => p.w < 160 || p.h < 72)) fail('has more supporting content than this composition can show. Split the slide or select a full-width composition; text is never dropped or shrunk.');
  return {
    slide: slide.id, layout_variant: variant, legacy_layout: slide.layout,
    key_message: brief.key_message, primary_block_id: primary.id,
    reading_order: [...order], visual_reason: brief.visual_reason,
    theme: slide.theme ?? (['timeline_focus', 'cover_focus'].includes(variant) ? 'dark' : 'light'),
    hierarchy: 'One primary evidence object, with supporting content sized to its role and length.',
    area_encoding: variant === 'market_layers' ? 'indentation shows scope sequence, not proportional market area' : 'none',
    placements,
  };
}
