// Firefox blocks Dark Reader from reading an external file: stylesheet.
// Import the styles through a classic script so there is one shared definition
// and the resulting stylesheet remains accessible in the page's document.
(() => {
  const style = document.createElement('style');
  style.textContent = `
body { margin: 0; }
#drawings { min-height: 100svh; }
#drawings > svg, #drawings img {
  display: block;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 100svh;
  margin-inline: auto;
  background: white;
}
#viewer-error { margin: 1rem; font: 1rem system-ui, sans-serif; }

.drawing-nav {
  position: fixed;
  z-index: 10;
  right: max(.75rem, env(safe-area-inset-right));
  bottom: max(.75rem, env(safe-area-inset-bottom));
  transform-origin: bottom right;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: .35rem;
  padding: .4rem;
  border: 1px solid #cbd5e1;
  border-radius: .6rem;
  background: #f4f7fa;
  box-shadow: 0 2px 8px #0003;
  font: 600 .875rem system-ui, sans-serif;
}
.drawing-nav a {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 3.5rem;
  min-height: 44px;
  padding: 0 .45rem;
  border: 1px solid #cbd5e1;
  border-radius: .3rem;
  background: white;
  color: #192c3a;
  text-decoration: none;
}
.drawing-nav a:hover { background: #e2e8f0; }
.drawing-nav a:focus-visible { outline: 3px solid #286bbb; outline-offset: 2px; }

@media print {
  .drawing-nav { display: none; }
  #drawings { min-height: 0; }
  #drawings > svg, #drawings img { width: 100%; max-height: none; break-after: page; }
  #drawings > svg:last-child, #drawings img:last-child { break-after: auto; }
}
`;
  document.head.append(style);
})();
