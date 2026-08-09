# New Data-Source Inventory

## PCA reference bundle

The raw bundle contains ten official reference PDFs:

### Coconut varieties

- Open-pollinated tall varieties
- Open-pollinated dwarf varieties
- Coconut hybrids

These sheets provide reference attributes such as first flowering, nut yield, copra yield, fruit component weights, fatty-acid characteristics, and selected utilization characteristics. They will parameterize versioned priors and conversion rules. They are not farm-level supervised-learning records.

### Pest and disease references

- Coconut bud and nut rot
- Coconut leaf beetle
- Coconut rhinoceros beetle
- Asiatic palm weevil
- Coconut scale insect

These sources will be converted into pest-specific evidence definitions, symptoms, risk factors, spatial rules, conditional-loss functions, and management guidance. Taxonomic terminology must be preserved exactly and reviewed before it is merged with legacy pest labels.

### Fertilization references

- Organic fertilization
- Intermittent fertilizer application

These sources support selectable management scenarios and scheduling logic. They must not be interpreted as universally compulsory prescriptions.

## Brochure photographs

Four photographs cover:

- Light levels beneath coconut canopies and practical intercropping applications
- Coconut scale insect information and management guidance

Numerical tables visible in photographs require manual double-entry verification. Automatic OCR output must not become a production parameter without human comparison against the brochure.

## Farmer registry workbook

The workbook contains **17,798 records** across **12 municipality/city worksheets** and 13 columns:

- Region
- Province
- Municipality
- Barangay
- Last name
- First name
- Middle name
- Suffix
- Gender
- Absolute area
- Coconut area
- Number of trees
- Number of parcels

### Worksheet counts

| Worksheet | Records |
| --- | ---: |
| Banga | 2,787 |
| Koronadal City | 1,047 |
| General Santos City | 3,103 |
| Lake Sebu | 1,022 |
| Norala | 937 |
| Polomolok | 977 |
| Santo Niño | 479 |
| Surallah | 1,681 |
| Tampakan | 1,970 |
| Tantangan | 940 |
| T'Boli | 778 |
| Tupi | 2,077 |

### Initial quality flags

The audit intentionally flags records for review rather than silently correcting them:

| Flag | Records/groups |
| --- | ---: |
| Positive coconut area with zero trees | 1,536 |
| Positive trees with zero coconut area | 580 |
| Coconut area greater than absolute area | 76 |
| Zero absolute area with positive coconut area | 23 |
| Tree density above 1,000 trees/ha | 13 |
| Positive density below 10 trees/ha | 100 |
| Suspected character-encoding artifacts | 479 |
| Duplicate identity groups | 337 groups / 847 records |

Extreme values include declared absolute area of 5,001.8 ha, coconut area of 20,105 ha, 20,000 trees, and 5,000 trees/ha. These are review flags, not automatic declarations that the source is wrong.

## Privacy classification

The farmer workbook contains personally identifiable information. It is stored under `data_sources/raw/`, excluded from Git, and must be processed through a restricted staging layer. Analytical records will use pseudonymous identifiers. Names must not be sent to CoCO-PILOT or any external model provider.
