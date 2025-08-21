import React from 'react';

export default function CyberThemeInit() {
  React.useEffect(() => {
    // Automatically apply cyber theme on app load
    document.documentElement.setAttribute('data-theme', 'cyber');
  }, []);

  return null; // This component just initializes the theme, doesn't render anything
}


