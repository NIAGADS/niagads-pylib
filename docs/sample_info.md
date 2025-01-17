# Sample Information

**Title:** Sample Information

|                           |                                                                              |
| ------------------------- | ---------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                     |
| **Required**              | No                                                                           |
| **Additional properties** | [Each additional property must conform to the schema](#additionalProperties) |

**Description:** description of required fields and field values for DSS Data Submission Sample Info Metadata

| Property                           | Pattern | Type           | Deprecated | Definition | Title/Description                                                                          |
| ---------------------------------- | ------- | -------------- | ---------- | ---------- | ------------------------------------------------------------------------------------------ |
| + [sample_id](#sample_id )         | No      | string         | No         | -          | sample IDs must be unique for each subject-source-experiment triple across the submission. |
| + [subject_id](#subject_id )       | No      | string         | No         | -          | must match a subject ID in the \`Subject Info\` metadata file.                             |
| - [sample_source](#sample_source ) | No      | string or null | No         | -          | (Optional) biosource for the sample; e.g., blood, brain tissue, plasma                     |
| - [comment](#comment )             | No      | string or null | No         | -          | any additional notes or caveats about the sample                                           |
| - [](#additionalProperties )       | No      | string or null | No         | -          | -                                                                                          |

## <a name="sample_id"></a>1. Property `Sample Information > sample_id`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** sample IDs must be unique for each subject-source-experiment triple across the submission.

## <a name="subject_id"></a>2. Property `Sample Information > subject_id`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** must match a subject ID in the `Subject Info` metadata file.

## <a name="sample_source"></a>3. Property `Sample Information > sample_source`

|              |                  |
| ------------ | ---------------- |
| **Type**     | `string or null` |
| **Required** | No               |

**Description:** (Optional) biosource for the sample; e.g., blood, brain tissue, plasma

## <a name="comment"></a>4. Property `Sample Information > comment`

|              |                  |
| ------------ | ---------------- |
| **Type**     | `string or null` |
| **Required** | No               |

**Description:** any additional notes or caveats about the sample

## <a name="additionalProperties"></a>5. Property `Sample Information > additionalProperties`

|              |                  |
| ------------ | ---------------- |
| **Type**     | `string or null` |
| **Required** | No               |

----------------------------------------------------------------------------------------------------------------------------
Generated using [json-schema-for-humans](https://github.com/coveooss/json-schema-for-humans) on 2025-01-17 at 10:24:20 -0500
