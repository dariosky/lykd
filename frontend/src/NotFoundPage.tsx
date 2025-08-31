export default function NotFoundPage() {
  return (
    <div style={{ textAlign: "center", padding: "48px 16px" }}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="180"
        height="180"
        viewBox="0 0 512 512"
        role="img"
        aria-labelledby="title desc"
        style={{ marginBottom: 24 }}
      >
        <title id="title">
          Vinyl record broken with angled irregular crack
        </title>
        <desc id="desc">
          A full circular vinyl disk, cracked diagonally across with a jagged,
          irregular gap.
        </desc>
        <defs>
          <mask id="crackMask" maskUnits="userSpaceOnUse">
            <rect x="0" y="0" width="512" height="512" fill="white" />
            <circle cx="256" cy="256" r="12" fill="black" />
            <path
              d="M 40 200 L 110 220 L 150 260 L 200 240 L 250 280 L 300 260 L 340 300 L 390 280 L 450 320 L 480 300"
              fill="none"
              stroke="black"
              strokeWidth={26}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </mask>
          <radialGradient id="shine" cx="35%" cy="30%" r="70%">
            <stop offset="0" stopColor="#ffffff" stopOpacity="0.15" />
            <stop offset="0.5" stopColor="#ffffff" stopOpacity="0.06" />
            <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g mask="url(#crackMask)">
          <circle cx="256" cy="256" r="220" fill="#111" />
          <circle cx="256" cy="256" r="95" fill="#ff4d4d" />
          <g fill="none" stroke="#fff" strokeOpacity="0.15" strokeWidth={1}>
            <circle cx="256" cy="256" r="210" />
            <circle cx="256" cy="256" r="195" />
            <circle cx="256" cy="256" r="180" />
            <circle cx="256" cy="256" r="165" />
            <circle cx="256" cy="256" r="150" />
            <circle cx="256" cy="256" r="135" />
          </g>
          <circle
            cx="256"
            cy="256"
            r="18"
            fill="none"
            stroke="#fff"
            strokeWidth={3}
            strokeOpacity="0.35"
          />
          <circle cx="256" cy="256" r="220" fill="url(#shine)" />
        </g>
        <path
          d="M 40 200 L 110 220 L 150 260 L 200 240 L 250 280 L 300 260 L 340 300 L 390 280 L 450 320 L 480 300"
          fill="none"
          stroke="#dcdcdc"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.7}
        />
        <path
          d="M 40 220 L 110 240 L 150 280 L 200 260 L 250 300 L 300 280 L 340 320 L 390 300 L 450 340 L 480 320"
          fill="none"
          stroke="#dcdcdc"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.4}
        />
      </svg>
      <h1 style={{ fontSize: 32, color: "#1db954", marginBottom: 12 }}>
        404 - Page Not Found
      </h1>
    </div>
  );
}
