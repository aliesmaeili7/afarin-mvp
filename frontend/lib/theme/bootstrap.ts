/**
 * Blocking script inlined in <head> so the first paint already has the
 * resolved dark class. Preference is read from the same cookie the layout uses.
 */
export const THEME_BOOTSTRAP_SCRIPT = `(function(){try{var m=document.cookie.match(/(?:^|; )afarin_theme=([^;]*)/);var pref=m?decodeURIComponent(m[1]):"system";if(pref!=="light"&&pref!=="dark"&&pref!=="system")pref="system";var dark=pref==="dark"||(pref==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);var r=document.documentElement;r.classList.toggle("dark",dark);r.setAttribute("data-theme",pref);}catch(e){}})();`;
