// The original decides "mobile" from the user agent, not the viewport width.
export const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile/i.test(navigator.userAgent)

export const lerp = (a, b, t) => a + (b - a) * t
