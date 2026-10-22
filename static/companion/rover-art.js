/* Rover-style helper dog: an ORIGINAL vector character (not Microsoft artwork).
   Pure markup only; all motion lives in companion.css, all behaviour in companion.js.
   viewBox is 120x130, the dog sits in the lower middle, props/effects live around it. */
window.ROVER_SVG = `
<svg class="rover" viewBox="0 0 120 130" data-pose="sleep" role="img" aria-label="Helper dog">
  <ellipse class="r-shadow" cx="60" cy="124" rx="38" ry="5"/>

  <g class="r-all">
    <!-- tail (behind the body) -->
    <g class="r-tail"><path d="M82 108 C100 106 108 92 101 76"/></g>

    <!-- body -->
    <g class="r-torso">
      <ellipse class="fur" cx="60" cy="97" rx="27" ry="27"/>
      <ellipse class="belly" cx="60" cy="103" rx="15" ry="19"/>
      <ellipse class="fur" cx="40" cy="121" rx="14" ry="6"/>
      <ellipse class="fur" cx="80" cy="121" rx="14" ry="6"/>
      <g class="r-arms-down">
        <path class="fur-stroke" d="M45 84 L43 113"/>
        <path class="fur-stroke" d="M75 84 L77 113"/>
        <ellipse class="paw" cx="43" cy="117" rx="8" ry="5"/>
        <ellipse class="paw" cx="77" cy="117" rx="8" ry="5"/>
      </g>
    </g>

    <!-- collar -->
    <path class="collar" d="M40 70 Q60 84 80 70"/>
    <circle class="tag" cx="60" cy="78.5" r="3.6"/>

    <!-- arms raised to hold a prop -->
    <g class="p-hold r-arms-hold">
      <path class="fur-stroke" d="M45 82 L37 100"/>
      <path class="fur-stroke" d="M75 82 L83 100"/>
    </g>

    <!-- props -->
    <g class="r-book">
      <path d="M33 107 L33 86 Q47 81 60 87 Q73 81 87 86 L87 107 Q73 102 60 108 Q47 102 33 107Z" fill="#2f5fb3"/>
      <path d="M36 104 L36 88 Q48 85 60 89.5 L60 105 Q48 100 36 104Z" fill="#fff"/>
      <path d="M60 89.5 Q72 85 84 88 L84 104 Q72 100 60 105Z" fill="#fff"/>
      <path d="M40 93 Q48 91 56 94 M40 98 Q48 96 56 99 M64 94 Q72 91 80 93 M64 99 Q72 96 80 98" fill="none" stroke="#9db3d6" stroke-width="1.1"/>
      <path class="page-flip" d="M60 89.5 Q72 85 84 88 L84 104 Q72 100 60 105Z"/>
    </g>
    <g class="r-notepad">
      <rect x="40" y="86" width="40" height="23" rx="2.5" fill="#fffbe6" stroke="#b9a35a" stroke-width="1" transform="rotate(-4 60 98)"/>
      <path d="M46 94 H74 M46 99 H74 M46 104 H66" fill="none" stroke="#9db3d6" stroke-width="1" transform="rotate(-4 60 98)"/>
      <g class="r-pencil">
        <path d="M68 98 L82 82" stroke="#f2c230" stroke-width="4" stroke-linecap="round"/>
        <path d="M68 98 L66.6 99.6" stroke="#3a2a1a" stroke-width="3.2" stroke-linecap="round"/>
        <path d="M82 82 L84 79.7" stroke="#e58a8a" stroke-width="4" stroke-linecap="round"/>
      </g>
    </g>
    <g class="r-lens">
      <line x1="88" y1="90" x2="99" y2="103" stroke="#6b4a2a" stroke-width="4" stroke-linecap="round"/>
      <circle cx="82" cy="82" r="11" fill="rgba(200,232,255,.5)" stroke="#3d5a9a" stroke-width="3"/>
      <path d="M76 77 Q79 74 83 74" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
      <ellipse class="paw" cx="94" cy="97" rx="6" ry="5"/>
    </g>

    <g class="p-hold r-paws-hold">
      <ellipse class="paw paw-l" cx="36" cy="102" rx="7" ry="6"/>
      <ellipse class="paw paw-r" cx="84" cy="102" rx="7" ry="6"/>
    </g>

    <!-- head -->
    <g class="r-head">
      <g class="r-ear r-ear-l"><ellipse class="ear" cx="35" cy="44" rx="9" ry="19" transform="rotate(8 35 44)"/></g>
      <g class="r-ear r-ear-r"><ellipse class="ear" cx="85" cy="44" rx="9" ry="19" transform="rotate(-8 85 44)"/></g>
      <ellipse class="fur" cx="60" cy="46" rx="27" ry="24"/>
      <ellipse class="muzzle" cx="60" cy="57" rx="15" ry="11"/>
      <ellipse class="nose" cx="60" cy="50.5" rx="6" ry="4"/>
      <ellipse cx="58.3" cy="49.2" rx="1.8" ry="1" fill="#fff" opacity=".6"/>
      <g class="r-eyes">
        <g class="eye-open">
          <ellipse class="eye-white" cx="49" cy="38" rx="6.5" ry="7.5"/>
          <ellipse class="eye-white" cx="71" cy="38" rx="6.5" ry="7.5"/>
          <g class="pupils">
            <circle class="pupil" cx="50" cy="39" r="3"/><circle class="glint" cx="51" cy="37.8" r=".9"/>
            <circle class="pupil" cx="72" cy="39" r="3"/><circle class="glint" cx="73" cy="37.8" r=".9"/>
          </g>
        </g>
        <g class="eye-closed"><path d="M43 39 Q49 44 55 39"/><path d="M65 39 Q71 44 77 39"/></g>
        <g class="eye-happy"><path d="M43 41 Q49 34 55 41"/><path d="M65 41 Q71 34 77 41"/></g>
      </g>
      <path class="mouth" d="M52 61 Q60 67 68 61"/>
      <g class="mouth-open">
        <path d="M51 60 Q60 78 69 60Z" fill="#7a1f1f"/>
        <ellipse cx="60" cy="68" rx="5" ry="3.4" fill="#ff8aa0"/>
      </g>
      <ellipse class="r-tear" cx="44" cy="47" rx="1.8" ry="2.6"/>
    </g>
  </g>

  <!-- effects -->
  <g class="r-zzz">
    <text x="88" y="34" font-size="11">z</text>
    <text x="96" y="22" font-size="14">z</text>
    <text x="104" y="9" font-size="17">Z</text>
  </g>
  <text class="r-q" x="90" y="26" font-size="24">?</text>
  <g class="r-spark">
    <path transform="translate(20 24)" d="M0 -7 L1.8 -1.8 L7 0 L1.8 1.8 L0 7 L-1.8 1.8 L-7 0 L-1.8 -1.8Z"/>
    <path transform="translate(100 16)" d="M0 -6 L1.5 -1.5 L6 0 L1.5 1.5 L0 6 L-1.5 1.5 L-6 0 L-1.5 -1.5Z"/>
    <path transform="translate(108 62)" d="M0 -5 L1.3 -1.3 L5 0 L1.3 1.3 L0 5 L-1.3 1.3 L-5 0 L-1.3 -1.3Z"/>
    <path transform="translate(10 66)" d="M0 -5 L1.3 -1.3 L5 0 L1.3 1.3 L0 5 L-1.3 1.3 L-5 0 L-1.3 -1.3Z"/>
  </g>
</svg>`;
