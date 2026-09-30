/** Rich Seed IR authoring. Artifact Tool is resolved by the portable Python launcher. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { planVisualComposition, readableValueAxis } from './visual_composition.mjs';

const [inputPath, outputDir, modulePath, pythonExecutable] = process.argv.slice(2);
if (!inputPath || !outputDir || !modulePath) throw new Error('Expected input.json output-directory artifact-tool-module');
const input = JSON.parse(await fs.readFile(inputPath, 'utf8'));
const { deck, profile, sources, project, font } = input;
// Register in the *same* skia-canvas instance used by Artifact Tool. A top-level
// canvas dependency may own another font registry and silently render fallbacks.
const artifactRequire = createRequire(pathToFileURL(modulePath));
const { FontLibrary, Canvas, loadImage } = artifactRequire('skia-canvas');
const fontPaths = [...new Set(font.paths ?? [font.path])].filter(Boolean);
if (!fontPaths.length) throw new Error('No discovered font file supplied by the portable launcher');
FontLibrary.use(font.selected, fontPaths);
if (!FontLibrary.has(font.selected)) throw new Error(`Could not register rendering font: ${font.selected}`);
const measurementContext = new Canvas(1, 1).getContext('2d');
const { Presentation, PresentationFile, FileBlob } = await import(pathToFileURL(modulePath).href);
const C = Object.fromEntries(Object.entries(profile.colors).map(([k, v]) => [k, '#' + v.replace(/^#/, '')]));
const cfg = profile.rich_layouts ?? {};
const W = cfg.width_px ?? 1280, H = cfg.height_px ?? 720;
const M = cfg.margin_px ?? 72, CW = W - M * 2;
const gap = cfg.gutter_px ?? 26;
const FAMILY = font.selected;
const BODY = deck.view === 'pitch' ? (cfg.pitch_body_px ?? 21) : (cfg.master_body_px ?? 19);
const TITLE = cfg.title_px ?? 44;
const p = Presentation.create({ slideSize: { width: W, height: H } });
const checks = [], coverage = [], nativeCharts = [], nativeTables = [], compositions = [];
const cropManifest = [];
let currentId, currentNumber, dark, fg, muted, headerShift = 0, pictureIndex = 0, currentComposition;

function objects(v) {
  if (Array.isArray(v)) return v.flatMap(objects);
  if (v && typeof v === 'object') return [v, ...Object.values(v).flatMap(objects)];
  return [];
}
function refs(s) { return [...new Set([...(s.evidence_ids ?? []), ...(s.governing_evidence_ids ?? []), ...(s.body ?? []).flatMap(b => b.evidence_ids ?? []), ...(s.visual?.evidence_ids ?? []), ...objects(s.blocks ?? []).flatMap(b => b.evidence_ids ?? [])])]; }
function disclose(value, kind) {
  const v = String(value ?? '');
  if (/^\s*(가정|가설|추정|예시|계획|목표|예정)\s*[:：]/.test(v)) return v;
  if (kind === 'fact' || !kind || (kind === 'plan' ? /계획|목표|예정|검증할/ : /가정|가설|추정|예시|가상/).test(v)) return v;
  return (kind === 'plan' ? '계획: ' : '가정: ') + v;
}
function rect(slide, x, y, w, h, fill, line = 'none') {
  return slide.shapes.add({ geometry: 'rect', position: { left: x, top: y, width: w, height: h }, fill, line: { fill: line, width: line === 'none' ? 0 : 1 } });
}
function rule(slide, x, y, w, color = C.accent) { return rect(slide, x, y, w, 2, color); }
function linesFor(value, size, width, bold = false) {
  // Measure the registered face and preserve explicit line breaks. The final
  // package is still re-imported and rendered: a metric estimate is not proof.
  measurementContext.font = `${bold ? 'bold ' : ''}${size}px "${FAMILY}"`;
  return String(value).split('\n').reduce((total, line) => {
    let count = 1, current = '';
    const tokens = line.match(/[\p{Script=Han}\p{Script=Hangul}\p{Script=Hiragana}\p{Script=Katakana}]|[^\s\p{Script=Han}\p{Script=Hangul}\p{Script=Hiragana}\p{Script=Katakana}]+|\s+/gu) ?? [];
    for (const token of tokens) {
      if (current && measurementContext.measureText(current + token).width > width - 6) { count++; current = ''; }
      if (measurementContext.measureText(token).width <= width - 6) current += token;
      else for (const character of token) {
        if (current && measurementContext.measureText(current + character).width > width - 6) { count++; current = ''; }
        current += character;
      }
    }
    return total + count;
  }, 0);
}
function text(slide, value, x, y, w, h, size = BODY, color = fg, bold = false, role = 'body', highlight = false) {
  const v = String(value ?? '');
  if (!v) return null;
  if (x < 0 || y < 0 || x + w > W + .01 || y + h > H + .01) throw new Error(`${currentId}: ${role} is outside the canvas`);
  const lines = linesFor(v, size, w, bold), allowed = Math.floor(h / (size * 1.18));
  if (lines > allowed) throw new Error(`${currentId}: ${role} needs about ${lines} lines in ${allowed}-line box. Expand the composition or edit this content: ${v}`);
  const s = slide.shapes.add({ geometry: 'textbox', name: `${currentId}:${role}`, position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { fill: 'none', width: 0 } });
  s.text = v;
  s.text.style = { typeface: FAMILY, fontSize: size, color, bold, lineSpacing: 1.12, autoFit: 'none', wrap: 'square', verticalAlignment: 'top', insets: { top: 0, bottom: 0, left: 0, right: 0 } };
  if (highlight) s.text = v.split('\n').map((line, i) => line.split(/(\d[\d,.]*(?:%|억|만|개월|년|원)?)/).map(run => ({ run, textStyle: { color: /^\d/.test(run) || currentComposition && i === 1 ? (dark ? C.accent_bright ?? '#FF654A' : C.accent) : color, bold, typeface: FAMILY, fontSize: `${size}px` } })));
  checks.push({ slide: currentId, role, estimated_lines: lines, allowed_lines: allowed, font_px: size, box_px: [x, y, w, h] });
  return s;
}
function heading(slide, b, x, y, w) {
  text(slide, disclose(b.title, b.kind), x, y, w, 52, 21, fg, true, b.id + ':heading');
}
function disclosure(slide, b, x, y, w) {
  if (b.disclosure) text(slide, b.disclosure, x, y, w, 34, 12, muted, false, b.id + ':disclosure');
}
async function imageAspectsFor(slide, blocks) {
  if (!['product_hero', 'cover_focus'].includes(slide.visual_brief?.layout_variant)) return {};
  const aspects = {};
  for (const b of blocks.filter(block => block.type === 'image')) {
    const source = path.resolve(project, b.path), rel = path.relative(project, source);
    if (rel.startsWith('..') || path.isAbsolute(rel)) throw new Error('Image escapes project');
    const image = await loadImage(source);
    const crop = b.crop ?? {};
    const width = image.width * (1 - (crop.left ?? 0) - (crop.right ?? 0));
    const height = image.height * (1 - (crop.top ?? 0) - (crop.bottom ?? 0));
    if (!(width > 0 && height > 0)) throw new Error(`${slide.id}: image ${b.id} has no visible dimensions`);
    aspects[b.id] = width / height;
  }
  return aspects;
}
async function picture(slide, asset, x, y, w, h) {
  const source = path.resolve(project, asset.path);
  const rel = path.relative(project, source);
  if (rel.startsWith('..') || path.isAbsolute(rel)) throw new Error('Image escapes project');
  const bytes = new Uint8Array(await fs.readFile(source));
  const captionSize = currentComposition ? 14 : 12;
  const caption = disclose(asset.caption, asset.kind);
  const captionHeight = Math.max(32, Math.ceil(linesFor(caption, captionSize, w) * captionSize * 1.18));
  const imageHeight = h - captionHeight - 8;
  if (imageHeight < 70) throw new Error(`${currentId}: image and full caption need more room. Enlarge ${asset.id ?? asset.path}.`);
  slide.images.add({ blob: bytes, contentType: /\.jpe?g$/i.test(source) ? 'image/jpeg' : 'image/png', alt: asset.alt, fit: 'contain', ...(asset.crop ? { crop: asset.crop } : {}), position: { left: x, top: y, width: w, height: imageHeight } });
  if (asset.crop) cropManifest.push({ slide: currentNumber, image_index: pictureIndex, crop: asset.crop, source, frame: [x, y, w, imageHeight] });
  pictureIndex++;
  text(slide, caption, x, y + imageHeight + 8, w, captionHeight, captionSize, muted, false, 'image-caption');
}
async function renderBlock(slide, b, x, y, w, h, opts = {}) {
  if (!opts.absolute && y < 550 && headerShift) { y += headerShift; h -= headerShift; }
  const noHeading = opts.noHeading ?? false;
  const headSize = opts.headingSize ?? 21;
  const headH = noHeading || !b.title ? 0 : opts.absolute ? Math.ceil(linesFor(disclose(b.title, b.kind), headSize, w, true) * headSize * 1.18) + 12 : 52;
  if (!noHeading && b.title) text(slide, disclose(b.title, b.kind), x, y, w, headH - (opts.absolute ? 8 : 0), headSize, opts.headingColor ?? fg, true, b.id + ':heading');
  const yy = y + headH;
  const disclosureSize = opts.absolute ? 14 : 12;
  const disclosureH = b.disclosure ? Math.max(36, Math.ceil(linesFor(b.disclosure, disclosureSize, w) * disclosureSize * 1.18) + 8) : 0;
  const hh = h - headH - disclosureH;
  if (b.type === 'text') text(slide, noHeading ? disclose(b.text, b.kind) : b.text, x, yy, w, hh, opts.fontSize ?? BODY, fg, false, b.id + ':text');
  else if (b.type === 'metric') {
    const valueSize = opts.metricSize ?? 48, valueH = Math.ceil(valueSize * 1.25);
    text(slide, b.value, x, yy, w, valueH, valueSize, C.accent, true, b.id + ':value');
    text(slide, noHeading ? disclose(b.detail, b.kind) : b.detail, x, yy + valueH + 6, w, hh - valueH - 6, opts.fontSize ?? 18, fg, false, b.id + ':detail');
  } else if (b.type === 'image') await picture(slide, b, x, yy, w, hh);
  else if (b.type === 'table') {
    if (noHeading && b.kind !== 'fact') text(slide, disclose(b.title, b.kind), x, yy - 25, w, 22, 12, C.accent, true, b.id + ':status');
    const values = [b.columns, ...b.rows], rows = values.length, cols = b.columns.length;
    const sz = opts.tableSize ?? opts.fontSize ?? (cols > 4 ? 15 : 17);
    const rawWidths = b.column_widths ?? (opts.semanticStyle === 'comparison' && cols === 3 ? [.22, .40, .38] : Array(cols).fill(1));
    const totalWidth = rawWidths.reduce((a, b) => a + b, 0);
    const widths = rawWidths.map(v => v / totalWidth * w);
    const rowNeeds = values.map((row, ri) => Math.max(...row.map((cell, ci) => linesFor(cell, sz, widths[ci] - 28, ri === 0 || ci === 0))) * sz * 1.18 + 16);
    const needed = rowNeeds.reduce((a, b) => a + b, 0);
    if (needed > hh) throw new Error(`${currentId}: table ${b.id} needs ${Math.ceil(needed)}px; available ${Math.floor(hh)}px. Allocate more room or split the complete table.`);
    const rowHeights = rowNeeds.map(v => v + (hh - needed) / rows);
    values.forEach((row, ri) => row.forEach((cell, ci) => {
      const lineCount = linesFor(cell, sz, widths[ci] - 28, ri === 0 || ci === 0);
      if (lineCount * sz * 1.18 > rowHeights[ri] - 12) throw new Error(`${currentId}: table ${b.id} row ${ri + 1} col ${ci + 1} needs more height: ${cell}`);
    }));
    const t = slide.tables.add({ rows, columns: cols, left: x, top: yy, width: w, height: hh, columnWidths: widths, values });
    t.borders.assign({ fill: dark ? C.line : '#DAD8D2', width: 1, style: 'solid' });
    t.cells.block({ row: 0, column: 0, rowCount: rows, columnCount: cols }).assign({ margins: { top: 8, bottom: 8, left: 14, right: 14 }, textStyle: { typeface: FAMILY, fontSize: sz, color: fg }, fill: dark ? C.panel : '#FFFFFF' });
    for (let ri = 0; ri < rows; ri++) {
      t.rows[ri].height = rowHeights[ri];
      for (let ci = 0; ci < cols; ci++) {
        const cell = t.getCell(ri, ci);
        cell.text.style = { typeface: FAMILY, fontSize: sz, color: ri === 0 ? '#FFFFFF' : fg, bold: ri === 0 || ci === 0, autoFit: 'none', wrap: 'square', verticalAlignment: 'middle' };
        if (ri === 0) cell.fill = C.ink;
        if (ci === 0 && ri > 0 && opts.semanticStyle === 'comparison') { cell.fill = dark ? '#282C36' : C.pale ?? '#FAE9E3'; cell.text.color = dark ? C.white : C.accent; }
        if (ci === cols - 1 && ri > 0 && b.highlight_last_column) { cell.fill = dark ? '#2D2725' : '#FBE3DB'; cell.text.color = dark ? '#FFFFFF' : C.ink; }
      }
    }
    nativeTables.push(currentNumber);
  } else if (b.type === 'chart') {
    const colorSeries = [C.accent, C.teal_dark, C.gold, C.muted];
    const labelStyle = { typeface: FAMILY, fontSize: opts.absolute ? 17 : 14, fill: fg };
    const decimals = Math.min(6, Math.max(...b.series.flatMap(s => s.values).map(v => (String(v).split('.')[1] ?? '').length)));
    const numberFormat = b.number_format ?? ('#,##0' + (decimals ? '.' + '0'.repeat(decimals) : ''));
    const isNonnegativeBar = b.chart_type === 'bar' && b.series.every(s => s.values.every(v => v >= 0));
    const isHorizontal = (b.chart_type ?? 'bar') === 'bar' && (b.direction ?? 'bar') === 'bar';
    const valueAxis = currentComposition && isNonnegativeBar ? readableValueAxis(b.series.flatMap(s => s.values)) : isNonnegativeBar ? { min: 0 } : {};
    slide.charts.add(b.chart_type ?? 'bar', { position: { left: x, top: yy + 25, width: w, height: hh - 25 }, categories: b.categories,
      series: b.series.map((s, i) => ({ name: disclose(s.name, s.kind ?? b.kind), values: s.values, fill: colorSeries[i % colorSeries.length], line: { fill: colorSeries[i % colorSeries.length], width: 3 }, valuesFormatCode: numberFormat })),
      hasLegend: b.series.length > 1 || b.series.some(s => s.kind && s.kind !== b.kind), legend: { position: 'bottom', textStyle: labelStyle },
      barOptions: { direction: b.direction ?? 'bar', grouping: 'clustered', gapWidth: 55 },
      chartFill: dark ? C.ink : C.paper, plotAreaFill: dark ? C.ink : C.paper,
      chartLine: { fill: 'none', width: 0 }, plotAreaLine: { fill: 'none', width: 0 },
      xAxis: { textStyle: labelStyle, numberFormatCode: 'General', ...(currentComposition && isHorizontal ? { orientation: 'maxMin' } : {}), line: { fill: 'none', width: 0 }, majorGridlines: null },
      yAxis: { textStyle: labelStyle, numberFormatCode: numberFormat, ...valueAxis, ...(currentComposition && isHorizontal ? { crosses: 'max', tickLabelPosition: 'low' } : {}), majorGridlines: { fill: dark ? C.line : '#D9D7D1', width: 1 } },
      titlePlacement: 'none', dataLabels: { showValue: true, position: 'outEnd', textStyle: { ...labelStyle, bold: true } } });
    text(slide, '단위: ' + b.unit, x, yy, w, 22, opts.absolute ? 14 : 12, muted, false, b.id + ':unit');
    nativeCharts.push(currentNumber);
  } else if (b.type === 'formula' && opts.semanticStyle === 'market_layers') {
    await marketLayers(slide, b, x, yy, w, hh);
  } else if ((b.type === 'roadmap' || b.type === 'steps') && opts.semanticStyle === 'execution_timeline') {
    await executionTimeline(slide, b, x, yy, w, hh);
  } else if (b.type === 'team' && opts.semanticStyle === 'team_roles') {
    await teamRoles(slide, b, x, yy, w, hh);
  } else if (b.type === 'steps' && opts.semanticStyle === 'featured_sequence') {
    await featuredSequence(slide, b, x, yy, w, hh);
  } else if (b.type === 'formula') {
    const rh = hh / b.items.length;
    for (let i = 0; i < b.items.length; i++) {
      const it = b.items[i], ry = yy + i * rh;
      rule(slide, x, ry + rh - 8, w, dark ? C.line : '#D5D2CA');
      text(slide, disclose(it.label, it.kind ?? b.kind), x, ry, w * .68, 30, 17, C.accent, true, b.id + ':label');
      text(slide, it.formula, x, ry + 34, w * .65, 58, 19, fg, false, b.id + ':formula');
      text(slide, it.result, x + w * .69, ry + 30, w * .31, 50, 29, C.accent, true, b.id + ':result');
      text(slide, it.basis, x, ry + rh - 47, w, 36, 13, muted, false, b.id + ':basis');
    }
  } else if (b.type === 'mapping') {
    const rh = hh / b.items.length;
    const cols = [w * .27, w * .30, w * .37], xs = [x, x + w * .30, x + w * .63];
    const columnLabels = b.column_labels ?? ['고객이 겪는 문제', '제품의 대응', '검증 근거와 기준'];
    if (!Array.isArray(columnLabels) || columnLabels.length !== 3 || columnLabels.some(v => typeof v !== 'string' || !v.trim())) throw new Error(`${currentId}: mapping.column_labels must contain three nonempty labels`);
    columnLabels.forEach((v, i) => text(slide, v, xs[i], yy, cols[i], 30, 14, muted, true, 'mapping-column'));
    for (let i = 0; i < b.items.length; i++) {
      const it = b.items[i], ry = yy + 42 + i * ((hh - 42) / b.items.length), rh2 = (hh - 42) / b.items.length;
      rule(slide, x, ry, w, dark ? C.line : '#D5D2CA');
      [it.problem, it.solution, it.proof].forEach((v, j) => text(slide, j === 0 ? disclose(v, it.kind ?? b.kind) : v, xs[j], ry + 15, cols[j], rh2 - 22, j === 2 ? 16 : 18, j === 1 ? C.accent : fg, j === 1, b.id + ':mapping'));
    }
  } else if (b.type === 'steps' || b.type === 'roadmap' || b.type === 'team') {
    const n = b.items.length, iw = (w - gap * (n - 1)) / n;
    for (let i = 0; i < n; i++) {
      const it = b.items[i], xx = x + i * (iw + gap), accent = [C.accent, '#EF7941', C.gold, dark ? C.teal : C.teal_dark][i % 4];
      if (b.type === 'roadmap') {
        rule(slide, xx, yy + 6, iw, accent);
        text(slide, disclose(it.period, it.kind ?? b.kind), xx, yy + 24, iw, 28, 14, accent, true, b.id + ':period');
        text(slide, it.title, xx, yy + 60, iw, 58, 23, fg, true, b.id + ':stage');
        text(slide, it.deliverables.join('\n'), xx, yy + 126, iw, hh - 216, 16, fg, false, b.id + ':deliverables');
        text(slide, '다음 단계의 조건', xx, yy + hh - 84, iw, 24, 12, accent, true, b.id + ':gate-label');
        text(slide, it.gate, xx, yy + hh - 56, iw, 54, 16, fg, true, b.id + ':gate');
      } else if (b.type === 'steps') {
        text(slide, String(i + 1).padStart(2, '0'), xx, yy, iw, 34, 25, accent, true, b.id + ':step-no');
        rule(slide, xx, yy + 42, iw, accent);
        text(slide, disclose(it.title, it.kind ?? b.kind), xx, yy + 56, iw, 54, it.asset ? 20 : 22, fg, true, b.id + ':step-title');
        if (it.asset) {
          const imageH = Math.min(182, hh * .44);
          await picture(slide, { ...it.asset, kind: it.asset.kind ?? it.kind ?? b.kind }, xx, yy + 114, iw, imageH);
          const after = yy + 114 + imageH + 6;
          const detailH = it.detail ? 42 : 0;
          text(slide, it.text, xx, after, iw, yy + hh - after - detailH - 6, 16, fg, false, b.id + ':step-text');
          if (it.detail) text(slide, it.detail, xx, yy + hh - detailH, iw, detailH, 13, muted, false, b.id + ':step-detail');
        } else {
          text(slide, it.text, xx, yy + 132, iw, hh * .45, 22, fg, false, b.id + ':step-text');
          if (it.detail) text(slide, it.detail, xx, yy + hh - 102, iw, 98, 16, muted, false, b.id + ':step-detail');
        }
      } else {
        let offset = 0;
        if (it.asset) { await picture(slide, { ...it.asset, kind: it.asset.kind ?? it.kind ?? b.kind }, xx, yy, iw, 142); offset = 150; }
        text(slide, disclose(it.name, it.kind ?? b.kind), xx, yy + offset, iw, 40, 27, fg, true, b.id + ':name');
        text(slide, it.role, xx, yy + offset + 47, iw, 44, 18, C.accent, true, b.id + ':role');
        text(slide, it.proof, xx, yy + offset + 107, iw, (hh - offset - 122) * .58, 17, fg, false, b.id + ':proof');
        text(slide, it.contribution, xx, yy + offset + 112 + (hh - offset - 122) * .58, iw, (hh - offset - 122) * .42, 16, muted, false, b.id + ':contribution');
      }
    }
  } else throw new Error(`Unknown rich block: ${b.type}`);
  if (b.disclosure) text(slide, b.disclosure, x, y + h - disclosureH + 8, w, disclosureH - 8, disclosureSize, muted, false, b.id + ':disclosure');
  coverage.push({ slide: currentId, block: b.id, type: b.type, rendered: true });
}

function textHeight(value, size, width, bold = false) {
  return Math.ceil(linesFor(value, size, width, bold) * size * 1.18);
}
async function marketLayers(slide, b, x, y, w, h) {
  const count = b.items.length, rowGap = 14, rowH = (h - rowGap * (count - 1)) / count;
  for (let i = 0; i < count; i++) {
    const it = b.items[i], indent = Math.min(22 * i, w * .07), xx = x + indent, ww = w - indent, yy = y + i * (rowH + rowGap);
    const last = i === count - 1, surfaceDark = last || dark;
    const labelColor = surfaceDark ? C.gold : C.accent;
    const foreground = surfaceDark ? C.white : C.ink, secondary = surfaceDark ? C.muted_dark : C.muted;
    rect(slide, xx, yy, ww, rowH, last ? C.ink : dark ? C.panel : i === 0 ? C.white : C.pale ?? '#FAE9E3', dark || last ? 'none' : '#E3D6CD');
    const pad = 14, innerW = ww - pad * 2, split = innerW * .58;
    const label = disclose(it.label, it.kind ?? b.kind);
    const labelH = textHeight(label, 18, split - 16, true);
    const formulaH = textHeight(it.formula, 20, split - 16);
    const resultH = textHeight(it.result, 30, innerW - split, true);
    const basisH = textHeight(it.basis, 14, innerW);
    const needed = pad + Math.max(labelH + 7 + formulaH, resultH) + 7 + basisH + pad;
    if (needed > rowH) throw new Error(`${currentId}: market layer ${i + 1} needs ${needed}px, available ${Math.floor(rowH)}px. Expand the market body, separate supporting context, or split the complete formula.`);
    text(slide, label, xx + pad, yy + pad, split - 16, labelH, 18, labelColor, true, `${b.id}:layer-${i}:label`);
    const contentY = yy + pad + labelH + 7;
    text(slide, it.formula, xx + pad, contentY, split - 16, formulaH, 20, foreground, false, `${b.id}:layer-${i}:formula`);
    text(slide, it.result, xx + pad + split, yy + pad + Math.max(0, (labelH + 7 + formulaH - resultH) / 2), innerW - split, resultH, 30, last ? C.white : C.accent, true, `${b.id}:layer-${i}:result`);
    text(slide, it.basis, xx + pad, yy + rowH - pad - basisH, innerW, basisH, 14, secondary, false, `${b.id}:layer-${i}:basis`);
  }
}
async function executionTimeline(slide, b, x, y, w, h) {
  const n = b.items.length, itemGap = 22, iw = (w - itemGap * (n - 1)) / n;
  rule(slide, x, y + 42, w, dark ? C.line : '#DAD7D0');
  for (let i = 0; i < n; i++) {
    const it = b.items[i], xx = x + i * (iw + itemGap), last = i === n - 1;
    const accent = last ? C.accent_bright ?? '#FF654A' : dark ? C.gold : C.accent;
    const period = b.type === 'roadmap' ? disclose(it.period, it.kind ?? b.kind) : String(i + 1).padStart(2, '0');
    text(slide, period, xx, y, iw, 34, 21, accent, true, `${b.id}:${i}:period`);
    rect(slide, xx, y + 39, 8, 8, accent);
    const top = y + 62, cardH = h - 62, pad = 17, tw = iw - pad * 2;
    const cardDark = dark || last, mainColor = cardDark ? C.white : C.ink, soft = last && dark ? '#FFE9E3' : cardDark ? C.muted_dark : C.muted;
    rect(slide, xx, top, iw, cardH, last ? dark ? C.accent : C.ink : dark ? C.panel : C.white);
    const title = disclose(it.title, it.kind ?? b.kind), titleH = textHeight(title, 23, tw, true);
    let cursor = top + pad;
    text(slide, title, xx + pad, cursor, tw, titleH, 23, mainColor, true, `${b.id}:${i}:stage`); cursor += titleH + 16;
    const details = b.type === 'roadmap' ? it.deliverables.join('\n') : it.text;
    const detailH = textHeight(details, 18, tw);
    const gate = b.type === 'roadmap' ? it.gate : it.detail;
    const gateH = gate ? textHeight(gate, 17, tw, true) : 0;
    const gateY = top + cardH - pad - gateH;
    if (cursor + detailH + (gate ? 28 : 0) > (gate ? gateY : top + cardH - pad)) throw new Error(`${currentId}: ${b.id} timeline stage ${i + 1} needs more height. Use fewer stages per slide or move complete supporting blocks.`);
    text(slide, details, xx + pad, cursor, tw, detailH, 18, soft, false, `${b.id}:${i}:deliverables`);
    if (it.asset) throw new Error(`${currentId}: an execution timeline with item images needs product_hero so every source image remains visible`);
    if (gate) {
      rule(slide, xx + pad, gateY - 15, tw, last && dark ? '#EF8A78' : last ? C.accent : dark ? C.line : '#DAD7D0');
      text(slide, gate, xx + pad, gateY, tw, gateH, 17, last ? dark ? C.white : C.gold : cardDark ? C.white : C.accent, true, `${b.id}:${i}:gate`);
    }
  }
}
async function teamRoles(slide, b, x, y, w, h) {
  const n = b.items.length, iw = (w - gap * (n - 1)) / n;
  for (let i = 0; i < n; i++) {
    const it = b.items[i], xx = x + i * (iw + gap), pad = 18, tw = iw - pad * 2;
    const cardDark = i === 0 || dark;
    rect(slide, xx, y, iw, h, cardDark ? C.ink : C.white, cardDark ? 'none' : '#DDDAD4');
    rule(slide, xx, y, iw, i === 0 ? C.gold : C.accent);
    const main = cardDark ? C.white : C.ink, soft = cardDark ? C.muted_dark : C.muted;
    let cursor = y + pad;
    if (it.asset) { const ih = Math.min(142, h * .32); await picture(slide, { ...it.asset, kind: it.asset.kind ?? it.kind ?? b.kind }, xx + pad, cursor, tw, ih); cursor += ih + 12; }
    for (const [role, value, size, color, bold] of [
      ['name', disclose(it.name, it.kind ?? b.kind), 26, main, true],
      ['role', it.role, 20, cardDark ? C.gold : C.accent, true],
      ['proof', it.proof, 18, main, false],
      ['contribution', it.contribution, 18, soft, false],
    ]) {
      const th = textHeight(value, size, tw, bold);
      if (cursor + th > y + h - pad) throw new Error(`${currentId}: team ${b.id} person ${i + 1} ${role} needs more room; preserve the role and proof on a larger composition.`);
      text(slide, value, xx + pad, cursor, tw, th, size, color, bold, `${b.id}:${i}:${role}`);
      cursor += th + (role === 'role' ? 22 : 14);
    }
  }
}
async function featuredSequence(slide, b, x, y, w, h) {
  const n = b.items.length;
  if (n > 4) throw new Error(`${currentId}: product sequence ${b.id} has more than four stages; split without losing assets.`);
  const available = w - gap * (n - 1), firstWidth = n === 1 ? available : available * (n === 2 ? .56 : .36);
  let xx = x;
  for (let i = 0; i < n; i++) {
    const it = b.items[i], iw = i === 0 ? firstWidth : (available - firstWidth) / (n - 1);
    const title = disclose(it.title, it.kind ?? b.kind), titleH = textHeight(title, 22, iw, true);
    text(slide, String(i + 1).padStart(2, '0'), xx, y, iw, 28, 20, C.accent, true, `${b.id}:${i}:number`);
    rule(slide, xx, y + 35, iw, i === 0 ? C.accent : dark ? C.line : '#DAD7D0');
    text(slide, title, xx, y + 48, iw, titleH, 22, fg, true, `${b.id}:${i}:title`);
    let cursor = y + 48 + titleH + 10;
    const textH = textHeight(it.text, 18, iw), detailH = it.detail ? textHeight(it.detail, 14, iw) + 8 : 0;
    if (it.asset) {
      const imageH = y + h - cursor - textH - detailH - 12;
      await picture(slide, { ...it.asset, kind: it.asset.kind ?? it.kind ?? b.kind }, xx, cursor, iw, imageH);
      cursor += imageH + 12;
    }
    text(slide, it.text, xx, cursor, iw, textH, 18, fg, false, `${b.id}:${i}:text`);
    if (it.detail) text(slide, it.detail, xx, cursor + textH + 8, iw, detailH - 8, 14, muted, false, `${b.id}:${i}:detail`);
    xx += iw + gap;
  }
}
async function composeVisual(slide, s, blocks, plan) {
  const blockById = new Map(blocks.map(b => [b.id, b]));
  // DOM/native shape ordering follows the supplied reading order, even when the
  // largest visual sits on the right of a cover.
  for (const id of plan.reading_order) {
    const b = blockById.get(id), place = plan.placements.find(p => p.block_id === id);
    const saved = { dark, fg, muted };
    const panel = place.surface === 'contrast' || place.surface === 'paper';
    const padding = panel ? 20 : 0;
    if (panel) {
      dark = place.surface === 'contrast' ? !dark : false;
      fg = dark ? C.white : C.ink; muted = dark ? C.muted_dark : C.muted;
      rect(slide, place.x, place.y, place.w, place.h, dark ? C.ink : C.white, dark ? 'none' : '#DAD7D0');
    } else if (place.role === 'support') rule(slide, place.x, place.y - 8, place.w, dark ? C.line : '#DAD7D0');
    const isPrimary = place.role === 'primary';
    try {
      await renderBlock(slide, b, place.x + padding, place.y + padding, place.w - padding * 2, place.h - padding * 2, {
        absolute: true, headingSize: place.compact ? 18 : 20, headingColor: dark ? C.gold : C.accent,
        fontSize: place.compact ? 18 : isPrimary && b.type === 'text' ? 28 : 21,
        metricSize: isPrimary ? 64 : place.compact ? 30 : 42,
        tableSize: b.type === 'table' && b.columns.length > 4 ? 18 : 20,
        semanticStyle: place.semantic_style,
      });
    } finally { ({ dark, fg, muted } = saved); }
  }
}

function legacyBlocks(s) {
  const bs = (s.body ?? []).map((b, i) => ({ ...b, id: `${s.id}-body-${i}`, type: 'text', title: i === 0 ? '핵심 내용' : '', text: disclose(b.text, b.kind) }));
  for (const [i, a] of (s.assets ?? []).entries()) bs.push({ ...a, id: `${s.id}-image-${i}`, type: 'image', title: '', kind: 'fact', evidence_ids: [] });
  if (s.visual?.type === 'bar') bs.unshift({ ...s.visual, id: `${s.id}-chart`, title: '근거 데이터', type: 'chart', chart_type: 'bar', series: [{ name: s.visual.unit, values: s.visual.values }] });
  if (s.visual?.type === 'metrics') s.visual.values.forEach((value, i) => bs.unshift({ id: `${s.id}-metric-${i}`, type: 'metric', title: s.visual.categories[i], value: String(value), detail: s.visual.unit, kind: s.governing_kind }));
  return bs;
}
async function supportBand(slide, blocks, y = 592, h = 66) {
  if (!blocks.length) return;
  const cw = (CW - gap * (blocks.length - 1)) / blocks.length;
  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i], x = M + i * (cw + gap);
    if (b.type === 'text') {
      text(slide, disclose(b.title, b.kind), x, y, cw, 25, 15, C.accent, true, b.id + ':band-title');
      text(slide, b.text, x, y + 28, cw, h - 28, 15, fg, false, b.id + ':band-text');
      if (b.disclosure) throw new Error(`${currentId}: move support-band disclosure into the visible text or allocate a full block`);
      coverage.push({ slide: currentId, block: b.id, type: b.type, rendered: true });
    } else await renderBlock(slide, b, x, y, cw, h, { noHeading: true, fontSize: 15, metricSize: 34 });
  }
}
async function compose(slide, s, blocks) {
  const get = type => blocks.find(b => b.type === type), rest = (...used) => blocks.filter(b => !used.includes(b));
  if (s.layout === 'product_journey') {
    const main = get('steps'); await renderBlock(slide, main, M, 202, CW, 402, { noHeading: true });
    await supportBand(slide, rest(main), 615, 52);
  } else if (s.layout === 'milestone_roadmap') {
    const main = get('roadmap'), other = rest(main);
    await renderBlock(slide, main, M, 208, CW, other.length ? 336 : 448, { noHeading: true });
    if (other.length) {
      rule(slide, M, 564, CW, C.accent);
      await supportBand(slide, other, 584, 80);
    }
  } else if (s.layout === 'roadmap_funding') {
    const main = get('roadmap'), metric = get('metric'), other = rest(main, metric);
    await renderBlock(slide, main, M, 206, CW, 334, { noHeading: true });
    rule(slide, M, 563, CW, C.accent);
    if (metric) await renderBlock(slide, metric, M, 584, 280, 80, { noHeading: true, metricSize: 34, fontSize: 15 });
    let x = M + 314, width = CW - 314;
    for (const b of other) { await renderBlock(slide, b, x, 580, width / other.length - 15, 82, { noHeading: b.type === 'text', fontSize: 15 }); x += width / other.length; }
  } else if (s.layout === 'problem_solution') {
    const main = get('mapping'), other = rest(main), side = other.some(b => b.type === 'image');
    await renderBlock(slide, main, M, 210, side ? 792 : CW, side ? 435 : 354, { noHeading: true });
    if (side) { const sh = 435 / other.length; for (let i = 0; i < other.length; i++) await renderBlock(slide, other[i], M + 830, 210 + i * sh, CW - 830, sh - 16); }
    else await supportBand(slide, other, 600, 64);
  } else if (s.layout === 'market_model') {
    const main = get('formula'), other = rest(main);
    await renderBlock(slide, main, M, 207, 744, 440, { noHeading: true });
    let yy = 207, sh = 440 / other.length;
    for (const b of other) { await renderBlock(slide, b, M + 788, yy, CW - 788, sh - 16, { fontSize: 17 }); yy += sh; }
  } else if (s.layout === 'competition_matrix') {
    const main = get('table'), other = rest(main);
    await renderBlock(slide, main, M, 234, CW, 328, { noHeading: true, fontSize: 17 });
    await supportBand(slide, other, 595, 68);
  } else if (s.layout === 'team_evidence') {
    const main = get('team'); await renderBlock(slide, main, M, 208, CW, 354, { noHeading: true });
    await supportBand(slide, rest(main), 595, 68);
  } else if (s.layout === 'cover' || s.layout === 'closing') {
    const visual = blocks.find(b => ['image', 'chart'].includes(b.type)), other = rest(visual);
    const ww = visual ? 620 : CW;
    let yy = 270, step = Math.min(150, 350 / Math.max(other.length, 1));
    for (const b of other) { await renderBlock(slide, b, M, yy, ww, step - 12, { noHeading: b.type === 'text', fontSize: 25 }); yy += step; }
    if (visual) await renderBlock(slide, visual, 758, 240, 450, 375, { noHeading: true });
  } else {
    const visuals = blocks.filter(b => ['image', 'chart', 'table', 'formula', 'mapping', 'steps', 'roadmap', 'team'].includes(b.type));
    const other = blocks.filter(b => !visuals.includes(b));
    if (visuals.length >= 2) {
      const ww = (CW - gap) / 2;
      for (let i = 0; i < visuals.length; i++) await renderBlock(slide, visuals[i], M + i * (ww + gap), 204, ww, 338);
      await supportBand(slide, other, 583, 78);
    } else if (visuals.length === 1) {
      await renderBlock(slide, visuals[0], M, 210, 728, 432);
      let yy = 210, sh = 432 / Math.max(other.length, 1);
      for (const b of other) { await renderBlock(slide, b, 842, yy, 366, sh - 14, { fontSize: 18 }); yy += sh; }
    } else {
      // Quantitative or editorial evidence: separate hierarchy, never numbered empty rows.
      const metrics = blocks.filter(b => b.type === 'metric');
      if (metrics.length) {
        let xx = M, ww = CW / metrics.length;
        for (const b of metrics) { await renderBlock(slide, b, xx, 216, ww - 24, 226); xx += ww; }
        const texts = blocks.filter(b => b.type !== 'metric');
        const tw = CW / Math.max(texts.length, 1);
        for (let i = 0; i < texts.length; i++) await renderBlock(slide, texts[i], M + i * tw, 474, tw - 28, 175, { fontSize: 19 });
      } else {
        const ww = (CW - gap * (blocks.length - 1)) / Math.max(blocks.length, 1);
        for (let i = 0; i < blocks.length; i++) await renderBlock(slide, blocks[i], M + i * (ww + gap), 230, ww, 390);
      }
    }
  }
}

await fs.mkdir(outputDir, { recursive: true });
for (let index = 0; index < deck.slides.length; index++) {
  const s = deck.slides[index]; currentId = s.id; currentNumber = index + 1;
  pictureIndex = 0;
  headerShift = s.subtitle ? 24 : 0;
  const blocks = s.blocks ?? legacyBlocks(s);
  currentComposition = planVisualComposition(s, blocks, { ...cfg, block_image_aspects: await imageAspectsFor(s, blocks) });
  dark = currentComposition ? currentComposition.theme === 'dark' : ['cover', 'closing', 'milestone_roadmap', 'roadmap_funding'].includes(s.layout) || s.theme === 'dark';
  fg = dark ? C.white : C.ink; muted = dark ? C.muted_dark : C.muted;
  const slide = p.slides.add(); slide.background.fill = dark ? C.ink : C.paper;
  text(slide, `${String(index + 1).padStart(2, '0')}  ${input.section_labels[s.section] ?? s.section}`, M, 40, CW, 28, currentComposition ? 16 : 12, dark ? C.gold : C.accent, true, 'section');
  const isBookend = ['cover', 'closing'].includes(s.layout);
  text(slide, disclose(s.governing_message, s.governing_kind), M, 80, CW, currentComposition ? 118 : isBookend ? 136 : 112, currentComposition ? TITLE : isBookend ? 51 : TITLE, fg, true, 'title', true);
  if (s.subtitle) text(slide, s.subtitle, M, currentComposition ? 202 : isBookend ? 229 : 185, CW, currentComposition ? 29 : 26, currentComposition ? 20 : 16, muted, false, 'subtitle');
  if (currentComposition) {
    await composeVisual(slide, s, blocks, currentComposition);
    compositions.push(currentComposition);
  } else {
    await compose(slide, s, blocks);
    compositions.push({ slide: s.id, layout_variant: 'legacy', legacy_layout: s.layout, primary_block_id: null, reading_order: blocks.map(b => b.id), visual_reason: 'Legacy draft without a visual brief; original layout dispatch retained.', theme: dark ? 'dark' : 'light' });
  }
  const sourceRefs = refs(s);
  const sourceFooter = sourceRefs.map(id => `[${id}] ${sources[id]?.publisher ?? sources[id]?.source_id ?? '팀 제출자료'}`).join('   ');
  const imageSources = objects(blocks).filter(b => b.path).map(a => a.source);
  const footer = [sourceFooter, imageSources.length ? '이미지: ' + [...new Set(imageSources)].join('; ') : ''].filter(Boolean).join('  ');
  // Long bibliographic details stay in notes; reference IDs remain visible.
  if (currentComposition) rule(slide, M, 664, CW, dark ? C.line : '#DAD7D0');
  text(slide, footer.length > 160 ? sourceRefs.map(id => `[${id}]`).join(' ') + '  상세 출처는 발표자 노트' : footer, M, 678, 1040, 30, currentComposition ? 12 : 10, muted, false, 'source-footer');
  text(slide, `${index + 1} / ${deck.slides.length}`, W - M - 70, 678, 70, 22, currentComposition ? 13 : 11, muted, false, 'page');
  const notes = [s.speaker_notes, '', ...sourceRefs.map(id => `[${id}] ${JSON.stringify(sources[id])}`), '', ...imageSources.map(source => 'Image source: ' + source), '', JSON.stringify({ blocks: s.blocks, visual_brief: s.visual_brief, source_slide_ids: s.source_slide_ids ?? [] })];
  slide.speakerNotes.textFrame.setText(notes.join('\n'));
}
const candidate = path.join(outputDir, 'seed-ir-draft.pptx');
const authored = nativeCharts.length ? path.join(outputDir, 'authored.pptx') : candidate;
await (await PresentationFile.exportPptx(p)).save(authored);
if (cropManifest.length) {
  const manifestPath = path.join(outputDir, 'image-crops.json');
  await fs.writeFile(manifestPath, JSON.stringify(cropManifest));
  const script = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fix_native_image_crops.py');
  const result = spawnSync(pythonExecutable, [script, authored, manifestPath], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error('Native crop package repair failed: ' + result.stderr);
}
if (nativeCharts.length) {
  if (!input.chart_snapshot_helper) throw new Error('Portable chart workbook helper is required');
  const receipt = path.join(outputDir, 'chart-data-snapshot.json');
  const result = spawnSync(pythonExecutable, [input.chart_snapshot_helper, authored, candidate, '--workspace', outputDir, '--receipt', receipt], { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  if (result.status !== 0) throw new Error('Literal chart workbook materialization failed: ' + result.stderr + result.stdout);
}
// Reuse identical media parts without resampling images or altering geometry.
// This applies to every deck; no brand, icon atlas or special slide ID is needed.
const mediaHelper = path.join(path.dirname(fileURLToPath(import.meta.url)), 'deduplicate_pptx_media.py');
const mediaResult = spawnSync(pythonExecutable, [mediaHelper, candidate, '--report', path.join(outputDir, 'media-dedup-report.json')], { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
if (mediaResult.status !== 0) throw new Error('Media packaging failed: ' + mediaResult.stderr);
// Re-import the actual package, then render every slide. Storyboard is never render proof.
const actual = await PresentationFile.importPptx(await FileBlob.load(candidate));
if (actual.slides.items.length !== deck.slides.length) throw new Error('Exported slide count changed');
await fs.mkdir(path.join(outputDir, 'renders'), { recursive: true });
for (let i = 0; i < actual.slides.items.length; i++) {
  const slide = actual.slides.items[i];
  const name = `slide-${String(i + 1).padStart(2, '0')}`;
  const png = await slide.export({ format: 'png', scale: 1.25 });
  await fs.writeFile(path.join(outputDir, 'renders', name + '.png'), new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: 'layout' });
  await fs.writeFile(path.join(outputDir, 'renders', name + '.layout.json'), await layout.text());
  console.log(`Rendered ${deck.view} ${i + 1}/${deck.slides.length}`);
}
await fs.writeFile(path.join(outputDir, 'rich-render-report.json'), JSON.stringify({ engine: 'artifact-tool', view: deck.view, slide_count: deck.slides.length, actual_pptx_rendered: true, pptx_render_review: 'not_performed', font_registration: { family: FAMILY, face_count: fontPaths.length, registry: 'artifact-tool/skia-canvas', registered: FontLibrary.has(FAMILY) }, native_chart_owner_slides: [...new Set(nativeCharts)], native_table_owner_slides: [...new Set(nativeTables)], compositions, checks, coverage }, null, 2));
