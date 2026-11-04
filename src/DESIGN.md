# Redesign assets and source record

## Visual direction

Warm paper, blue-green ink, tactile layered materials and fine copper connections. Live text stays separate from artwork. The new vector brand mark uses two open interlocking curves; the wordmark uses self-hosted Manrope at weight 650.

## Generated assets

Generated using the built-in image generation tool. Full-resolution originals remain in the image-generation library. Website copies are optimized WebP assets:

- `src/site/assets/knowledge-landscape.webp`: hero background, versioning/context cover.
- `src/site/assets/knowledge-prism.webp`: source/evidence research and architecture cover.
- `src/site/assets/knowledge-dialogue.webp`: dialogue/transfer cover and project-section artwork.

These are editorial illustrations, not scientific evidence. Final asset hashes are the git blob hashes of the committed files (the design kit shipped a separate `asset-manifest.json`; it is not part of this repository).

## Final prompts

### Knowledge landscape

Use case: stylized-concept. Create a premium editorial illustration for the hero background of contract.place, a research website about meaning management, source provenance and knowledge contracts. Landscape aspect ratio 3:2. A striking sculptural landscape made from many thin sheets of archival paper, like a geological cross section or delicate topographic contours, folding into an open circular aperture on the RIGHT HALF, with a few fine copper threads linking the layers. Think tactile museum exhibition poster and scientific editorial artwork, not a software diagram. Warm ivory #F7F6F1 background merging seamlessly at every edge, deep blue-green #142C38 and petrol teal ink #087F8C, small subtle copper accents. Fine etched line work, paper grain, dramatic but soft directional light, shadows between sculpted layers, sophisticated depth. LEFT HALF quiet near-empty ivory negative space for live HTML headline. At the right a beautifully detailed organic architectural paper sculpture, not a globe or brain. No text, no letters, no labels, no logo, no UI, no glow, no generic network dots, no gradients as the subject. Original artwork. Output a finished high resolution image.

### Knowledge prism

Use case: stylized-concept. Original editorial research article cover illustration, landscape 3:2. Subject: a translucent deep petrol teal glass prism refracting a single fine warm copper thread into several precise branching paths across layered sheets of ivory archival paper, suggesting knowledge, provenance, evidence and semantic objects. An abstract still life in a quiet research library, no literal bookshelves. Tactile paper grain, etched contour lines and softly lit architectural shadows, high-end museum catalog art direction. Composition fills the frame with an asymmetrical striking object, warm paper #eee9dc, deep ink #142C38, teal #087F8C, restrained copper. Rich detail that reads beautifully in a research card or large article header. NO text, NO letters, NO logos, NO interface, NO watermarks, NO neon, NO artificial AI brain imagery. Flat background with carefully crafted physical material textures; elegant and intellectual.

### Knowledge dialogue

Use case: stylized-concept. A premium original research editorial cover, 3:2 landscape. Two sculptural deep teal forms like carved open shells or abstract folded pages facing each other across a small gap, joined by one delicate copper filament. Between them a small floating piece of ivory archival paper. Visual metaphor for dialogue, transfer and preserving meaning between agents. Background warm ivory archival paper with subtle fine etched topographic lines, gallery still life, soft sunlit shadows, sophisticated restrained composition, tactile materials. Palette ink blue green #142C38, petrol teal #087F8C, ivory #F7F6F1 and tiny copper accents. Rich but uncluttered artwork suitable for an academic blog cover. No text, letters, logo, interface, robots or brain. Do not draw a data diagram.

## Original publication figures

- `src/site/assets/architecture-original.jpg`: https://arcanada.ai/img/blog/meaning-management-knowledge-contract-architecture/transcript/IMG-030.jpg
- `src/site/assets/knowledge-v2-original.jpg`: https://arcanada.ai/img/blog/meaning-management-knowledge-contract-v2-en.jpg

Figures are kept distinct from the editorial cover art. Their source article, status and attribution remain visible on native article pages.
