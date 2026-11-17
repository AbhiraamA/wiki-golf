<!-- Pixel map of the hole (from design/mock.html). -->
<div class="tee-art">
  <svg
    class="px"
    viewBox="0 0 90 57.6"
    role="img"
    aria-label="Pixel map of the hole: tee at bottom left, a long fairway past two bunkers, flag on the green at top right"
  >
    <defs>
      <pattern id="rough" width="4" height="4" patternUnits="userSpaceOnUse">
        <rect x="0" y="0" width="1" height="1" fill="#286B40" />
        <rect x="2" y="2" width="1" height="1" fill="#286B40" />
      </pattern>
    </defs>
    <!-- sky and clouds -->
    <rect x="0" y="0" width="90" height="13" fill="#8CCFE0" />
    <rect x="0" y="13" width="90" height="10" fill="#B9E4E4" />
    <rect x="10" y="6" width="8" height="2" fill="#FFFFFF" />
    <rect x="8" y="8" width="13" height="2" fill="#FFFFFF" />
    <rect x="58" y="9" width="6" height="2" fill="#FFFFFF" />
    <rect x="55" y="11" width="12" height="2" fill="#FFFFFF" />
    <!-- tree line -->
    <rect x="0" y="22" width="90" height="5" fill="#4E9C6A" />
    <rect x="4" y="19" width="12" height="3" fill="#4E9C6A" />
    <rect x="7" y="17" width="6" height="2" fill="#4E9C6A" />
    <rect x="38" y="20" width="18" height="2" fill="#4E9C6A" />
    <rect x="43" y="18" width="8" height="2" fill="#4E9C6A" />
    <rect x="68" y="19" width="16" height="3" fill="#4E9C6A" />
    <rect x="72" y="17" width="7" height="2" fill="#4E9C6A" />
    <!-- rough -->
    <rect x="0" y="27" width="90" height="31" fill="#2F7A4A" />
    <rect x="0" y="27" width="90" height="31" fill="url(#rough)" />
    <!-- fairway -->
    <rect x="2" y="48" width="20" height="7" fill="#86C98A" />
    <rect x="10" y="44" width="22" height="4" fill="#86C98A" />
    <rect x="20" y="40" width="22" height="4" fill="#86C98A" />
    <rect x="32" y="36" width="22" height="4" fill="#86C98A" />
    <rect x="44" y="33" width="20" height="3" fill="#86C98A" />
    <!-- green -->
    <rect x="62" y="29" width="20" height="7" fill="#B4E08A" />
    <rect x="64" y="28" width="16" height="1" fill="#B4E08A" />
    <rect x="64" y="36" width="16" height="1" fill="#B4E08A" />
    <!-- bunkers -->
    <rect x="30" y="46" width="8" height="3" fill="#E9C977" />
    <rect x="29" y="47" width="10" height="1" fill="#E9C977" />
    <rect x="52" y="39" width="7" height="3" fill="#E9C977" />
    <rect x="51" y="40" width="9" height="1" fill="#E9C977" />
    <!-- tee and ball -->
    <rect x="4" y="50" width="7" height="3" fill="#B4E08A" />
    <rect x="6" y="49" width="2" height="2" fill="#FFFFFF" />
    <!-- cup and flag -->
    <rect x="73" y="32" width="3" height="1" fill="#142019" />
    <rect x="74" y="20" width="1" height="12" fill="#142019" />
    <rect x="75" y="20" width="6" height="1" fill="#E8452C" />
    <rect x="75" y="21" width="5" height="1" fill="#E8452C" />
    <rect x="75" y="22" width="3" height="1" fill="#E8452C" />
    <rect x="75" y="23" width="1" height="1" fill="#E8452C" />
  </svg>
</div>

<style>
  .tee-art {
    margin-top: 24px;
    box-shadow: var(--frame);
  }
  .tee-art svg {
    width: 100%;
    height: auto;
  }
</style>
