import { useState } from 'react';
import heroImg from '../assets/hero.png';
import viteLogo from '../assets/vite.svg';
import vueLogo from '../assets/vue.svg';
import { bindStyles, display, scopeAttributes } from '../presentation';
import styles from './HelloWorld.module.css';
export default function HelloWorld(input: {}) {
    const cx = bindStyles(styles);
    const [count, setCount] = useState(0);
    return (<><section {...scopeAttributes(input)} data-v-hello-world="" id="center"><div data-v-hello-world="" className={cx("hero")}><img data-v-hello-world="" src={heroImg} width="170" height="179" alt="" className={cx("base")}/>
    <img data-v-hello-world="" src={vueLogo} alt="Vue logo" className={cx("framework")}/>
    <img data-v-hello-world="" src={viteLogo} alt="Vite logo" className={cx("vite")}/></div>
    <div data-v-hello-world=""><h1 data-v-hello-world="">{"Get started"}</h1>
    <p data-v-hello-world="">{"Edit "}
    <code data-v-hello-world="">{"src/App.tsx"}</code>
    {" and save to test "}
    <code data-v-hello-world="">{"HMR"}</code></p></div>
    <button data-v-hello-world="" type="button" onClick={() => { setCount(count + 1); }} className={cx("counter")}>{" Count is "}
    {display(count)}</button></section>
    <div {...scopeAttributes(input)} data-v-hello-world="" className={cx("ticks")}></div>
    <section {...scopeAttributes(input)} data-v-hello-world="" id="next-steps"><div data-v-hello-world="" id="docs"><svg data-v-hello-world="" role="presentation" aria-hidden="true" className={cx("icon")}><use data-v-hello-world="" href="/icons.svg#documentation-icon"></use></svg>
    <h2 data-v-hello-world="">{"Documentation"}</h2>
    <p data-v-hello-world="">{"Your questions, answered"}</p>
    <ul data-v-hello-world=""><li data-v-hello-world=""><a data-v-hello-world="" href="https://vite.dev/" target="_blank"><img data-v-hello-world="" src={viteLogo} alt="" className={cx("logo")}/>
    {" Explore Vite "}</a></li>
    <li data-v-hello-world=""><a data-v-hello-world="" href="https://vuejs.org/" target="_blank"><img data-v-hello-world="" src={vueLogo} alt="" className={cx("button-icon")}/>
    {" Learn more "}</a></li></ul></div>
    <div data-v-hello-world="" id="social"><svg data-v-hello-world="" role="presentation" aria-hidden="true" className={cx("icon")}><use data-v-hello-world="" href="/icons.svg#social-icon"></use></svg>
    <h2 data-v-hello-world="">{"Connect with us"}</h2>
    <p data-v-hello-world="">{"Join the Vite community"}</p>
    <ul data-v-hello-world=""><li data-v-hello-world=""><a data-v-hello-world="" href="https://github.com/vitejs/vite" target="_blank"><svg data-v-hello-world="" role="presentation" aria-hidden="true" className={cx("button-icon")}><use data-v-hello-world="" href="/icons.svg#github-icon"></use></svg>
    {" GitHub "}</a></li>
    <li data-v-hello-world=""><a data-v-hello-world="" href="https://chat.vite.dev/" target="_blank"><svg data-v-hello-world="" role="presentation" aria-hidden="true" className={cx("button-icon")}><use data-v-hello-world="" href="/icons.svg#discord-icon"></use></svg>
    {" Discord "}</a></li>
    <li data-v-hello-world=""><a data-v-hello-world="" href="https://x.com/vite_js" target="_blank"><svg data-v-hello-world="" role="presentation" aria-hidden="true" className={cx("button-icon")}><use data-v-hello-world="" href="/icons.svg#x-icon"></use></svg>
    {" X.com "}</a></li>
    <li data-v-hello-world=""><a data-v-hello-world="" href="https://bsky.app/profile/vite.dev" target="_blank"><svg data-v-hello-world="" role="presentation" aria-hidden="true" className={cx("button-icon")}><use data-v-hello-world="" href="/icons.svg#bluesky-icon"></use></svg>
    {" Bluesky "}</a></li></ul></div></section>
    <div {...scopeAttributes(input)} data-v-hello-world="" className={cx("ticks")}></div>
    <section {...scopeAttributes(input)} data-v-hello-world="" id="spacer"></section></>);
}
