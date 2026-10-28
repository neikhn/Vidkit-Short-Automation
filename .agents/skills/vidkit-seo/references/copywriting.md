# Description and tag guidance

Read when writing or revising SEO copy. Reviewed: 2026-10-12.

## Description

Make the first one or two lines worth reading before “Show more”: name the topic with the primary keyword and a concrete question, surprise, useful distinction or supported development. Do not start every video with “In this video” / “Trong video này,” repeat its title verbatim or use generic hype.

Follow with one or two short sentences about what this specific video clarifies. Product demos describe the actual use case; mechanism explainers expose the important relation; news preserves who reported what and any uncertainty. Retain material limitations naturally rather than converting them into unsupported certainty.

End with a topic-specific invitation to follow/interact with HCDB AI (VI) or AI Lens (EN), relevant source links, then one line of 3–5 related hashtags. Use short paragraphs. The final description is one ready-to-paste string, at most 1,000 NFC code points including every newline/link/hashtag. The shape is guidance, not a sentence template to repeat.

Examples below assume a script explaining semantic search with document embeddings. They show tone only; do not reuse claims in unrelated videos or invent a source URL.

VI:
> Tìm tài liệu đúng ý dù không gõ đúng từ khóa? Tìm kiếm ngữ nghĩa so sánh các vector biểu diễn nội dung để tìm đoạn liên quan.
>
> Theo dõi và tương tác với HCDB AI để khám phá cách AI xử lý thông tin.
>
> #TimKiemNguNghia #Embeddings #AI

EN:
> How can semantic search find a passage without an exact keyword match? Document embeddings turn meaning into vectors that can be compared to find related text.
>
> Follow and interact with AI Lens for more explanations of how AI processes information.
>
> #SemanticSearch #Embeddings #AI

For a real package, insert verified source links before the hashtag line and count the resulting exact string. Do not copy research commentary into the upload description. In JSON, store hashtags separately for consistency checks; in Markdown, show them only inside this complete description.

## Tags: useful breadth, not filler

Build candidate terms from the approved content and observed market vocabulary:

| Group | Include when supported |
|---|---|
| Entity | Exact product/model/company name and genuine alternate spelling |
| Topic | The video's mechanism or category, such as document embeddings |
| Feature | A capability actually described, not unrelated features of the product |
| Viewer intent | Specific queries/use cases the video answers |
| Language/market | Natural local names and English technical terms used by that audience |

Rank exact entity/topic/intent terms before broad context. Cover different useful searches, not many reordered versions of one phrase. Use recognizable misspellings only when evidenced; do not fabricate them. VI may combine Vietnamese phrases with established English technical names; EN is not a translated Vietnamese keyword dump.

Aim for 450–500 characters after the YouTube count. If over 500, remove lowest-value, overlapping or broad tags until within the cap; do not cut a tag mid-phrase. If below 450, look for missing useful coverage across the groups, then accept a shorter set with a concrete `tagShortfallReason` if no more relevant terms exist. No minimum tag count or mandatory broad “viral/trending” tags.

Deduplicate after NFC/trim/casefold. Avoid unrelated competitor names, fabricated metrics and repetitive accented/unaccented variants without a reason. Hashtags remain in the description; comma-separated tags belong in YouTube's tags field.

## Editorial review

Check that the opening and explanation add value beyond the title; all claims match the script and sources; CTA fits the topic/channel; hashtags are relevant and appear once; each tag contributes distinct coverage. Record unsupported keyword performance as editorial inference, not measured demand.

Primary guidance: [YouTube description tips](https://support.google.com/youtube/answer/12948449?hl=en), [tag role](https://support.google.com/youtube/answer/146402?hl=en), checked 2026-10-12. Title/thumbnail/description carry more discovery weight than tags; 450–500 is a Vidkit coverage target, not a platform optimization guarantee.
