```markdown
# Buycott

**Buycott is a semantic, map-first civic discovery app that helps people find where specific products can likely be obtained locally.**

Instead of ranking businesses by popularity or profit, Buycott uses semantic inference and geographic proximity to show where an item can most likely be found nearby. The system is designed to strengthen local economies, increase civic resilience, and provide transparent, explainable discovery of real-world goods.

---

# Core Concept

Buycott answers a simple question:

> Where can I get this nearby?

When a user searches for an item (e.g., “birthday candles”, “USB-C cable”, “packing tape”), Buycott:

- Interprets the semantic meaning of the query
- Expands it using a structured ontology of product capabilities
- Matches it against locally extracted business information
- Displays likely locations on a map
- Shows how far away they are and the strength of the semantic match

Buycott does not recommend businesses. It reveals capability.

---

# Key Principles

Buycott is designed around the following architectural principles:

- **Semantic capability matching, not ranking**
- **Local-first discovery**
- **Explainable, transparent results**
- **No engagement-based or monetized prioritization**
- **Civic-aligned infrastructure**

All results are derived from semantic inference and geographic proximity.

---

# How It Works (High-Level)

The system operates as a semantic geographic capability index.

### 1. Data Extraction
Public information about businesses is extracted from:

- Official websites
- Public directories
- Public business listings

This text becomes the semantic knowledge base for each business.

---

### 2. Embedding and Ontology Mapping

Extracted business data is converted into semantic embeddings.

User queries are also converted into embeddings and expanded through an ontology hierarchy.

Example:





```

Example Use Cases

| User Query                  | Ontology Expansion Chain                                                   | Query Embedding Meaning                    | Business Embedding Source                         | Business Match                    | Similarity Score (Raw) | Evidence Strength (%) | Distance | User-Visible Explanation                         | Full Match Chain                                                                |
| --------------------------- | -------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------- | --------------------------------- | ---------------------- | --------------------- | -------- | ------------------------------------------------ | ------------------------------------------------------------------------------- |
| number 5 birthday candle    | birthday candle → cake decoration → baking supplies → bakery capability | birthday, candle, cake, celebration        | Website: “custom birthday cakes and desserts”   | Panadería La Esperanza           | 0.87                   | 87%                   | 3 min    | Website mentions birthday cakes and celebrations | candle → cake decoration → bakery → bakery embedding → match                |
| USB-C to Lightning cable    | charging cable → phone accessory → electronics capability                | phone charger, USB cable, device accessory | Website: “iPhone repair and accessories”        | TechFix Phone Repair              | 0.92                   | 92%                   | 4 min    | Website mentions phone accessories and charging  | cable → phone accessory → repair capability → repair shop embedding → match |
| 35mm film roll              | camera film → photography equipment → camera shop capability             | film, analog camera, photography           | Website: “film cameras and film development”    | Midwest Camera Exchange           | 0.94                   | 94%                   | 6 min    | Website mentions film and analog photography     | film → photography capability → camera shop embedding → match                |
| packing tape                | packaging supply → shipping supply → hardware capability                 | tape, packaging, moving supplies           | Website: “tools and moving supplies”            | Joe's Hardware                    | 0.89                   | 89%                   | 5 min    | Website mentions packaging and hardware supplies | packaging → hardware capability → hardware store embedding → match           |
| AA batteries                | portable power → electronics accessory → electronics capability          | battery, power supply, electronics         | Website: “electronics and accessories”          | Jeff's Electronics                | 0.91                   | 91%                   | 8 min    | Website mentions electronics and accessories     | battery → electronics capability → electronics store embedding → match       |
| screen protector for iPhone | screen protector → phone accessory → electronics capability              | phone protection, screen glass             | Website: “phone repair and protection services” | Abdul's Phone Repair MOA Kiosk #3 | 0.90                   | 90%                   | 2 min    | Website mentions phone repair and accessories    | protection → phone accessory → repair shop embedding → match                 |
| precision screwdriver       | screwdriver → hand tool → repair tool → hardware capability             | repair tool, screwdriver, maintenance      | Website: “tools and repair supplies”            | Jackson's Tools                  | 0.88                   | 88%                   | 7 min    | Website mentions tools and repair supplies       | tool → hardware capability → hardware store embedding → match                |
| birthday cake candles       | cake decoration → baking supplies → bakery capability                    | cake decoration, candle, celebration       | Website: “birthday cakes and celebration cakes” | Vikings Bakery                    | 0.86                   | 86%                   | 4 min    | Website mentions birthday cakes                  | cake decoration → bakery capability → bakery embedding → match               |
| camera battery charger      | camera charger → photography accessory → camera capability               | camera accessory, charger, photography     | Website: “camera accessories and gear”          | Minneapolis Camera Exchange      | 0.93                   | 93%                   | 9 min    | Website mentions camera accessories              | charger → photography capability → camera shop embedding → match             |
| moving box tape             | packaging supply → shipping supply → hardware capability                 | packaging, moving supplies                 | Website: “moving and storage supplies”          | Andy's Moving Supply             | 0.89                   | 89%                   | 6 min    | Website mentions moving supplies                 | packaging → moving supply capability → supply store embedding → match        |


```

This allows Buycott to infer capabilities even when items are not explicitly listed.

---

### 3. Semantic Matching

Buycott compares the query embedding to business embeddings using vector similarity search.

Businesses are identified based on semantic capability proximity, not popularity.

---

### 4. Map-Based Discovery

Results are displayed on a map showing:

- Business location
- Minutes away
- Evidence strength (semantic similarity indicator)

Users can immediately see what is available nearby.

---

# System Architecture

Buycott is structured in layers:

```

Extraction Layer
→ Embedding Layer
→ Ontology Layer
→ Semantic Search Layer
→ API Layer
→ Flutter Map UI

```

This modular architecture ensures scalability, transparency, and semantic consistency.

---

# Repository Structure

This repository contains the architectural and governance specifications for Buycott.

```

/docs
phase0.md
phase1.md
phase2.md
phase-summary.md
technical-architectural-blueprint.md

/README.md

```

These documents define:

- Governance and system invariants
- Ontology structure and semantic matching model
- Vertical slice implementation architecture
- Discovery and UX expansion features
- Full technical system blueprint

---

# Development Model

Buycott is developed using a vertical slice methodology.

Each slice includes:

- Extraction
- Embedding
- Ontology expansion
- Semantic search
- API layer
- UI layer

This ensures end-to-end validation of semantic correctness.

---

# Technology Stack

**Frontend**
- Flutter (Dart)
- Map-based UI

**Backend**
- Python or Node.js
- PostgreSQL with pgvector
- Vector similarity search

**Extraction**
- OpenClaw semantic extraction agents

**Infrastructure**
- GPU-enabled embedding generation
- Scalable semantic index

---

# System Identity

Buycott is a:

```

Semantic geographic capability index

```

Buycott is not a:

```

Recommendation engine
Advertising platform
Popularity-ranked directory
Engagement-optimized system

```

This distinction is fundamental to the system’s architecture.

---

# Goals

Buycott aims to:

- Increase visibility of local businesses
- Reduce dependence on centralized online marketplaces
- Improve real-world resource accessibility
- Strengthen local economic ecosystems
- Provide transparent and explainable discovery

---

# Status

Buycott is currently in the architectural and implementation phase.

Core semantic search and ontology infrastructure are defined and ready for implementation.

---

# License

License to be determined.

---

# Vision

Buycott transforms local discovery from a popularity contest into a semantic capability map of the real world.

Instead of asking:

> What is popular?

Buycott answers:

> What exists, and how close is it?
```
