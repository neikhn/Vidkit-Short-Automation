"""Channel names used by workflow v8+ narration and on-screen CTA."""

CHANNELS = {
    "vi": {"display": "HCDB AI", "spoken": "Hãy Cùng Bắt Đầu AI",
           "like": "Thích", "liked": "Đã thích", "subscribe": "Đăng ký", "subscribed": "Đã đăng ký"},
    "en": {"display": "AI Lens", "spoken": "AI Lens",
           "like": "Like", "liked": "Liked", "subscribe": "Subscribe", "subscribed": "Subscribed"},
}


def cta_props(language: str) -> dict[str, str]:
    channel = CHANNELS[language]
    return {"channelLabel": channel["display"], "locale": language,
            "likeLabel": channel["like"], "likedLabel": channel["liked"],
            "subscribeLabel": channel["subscribe"], "subscribedLabel": channel["subscribed"]}
