import { Children, cloneElement, isValidElement, useLayoutEffect, useRef, useState, type ReactElement, type ReactNode, type Ref } from 'react';
interface ChildProps {
    className?: string;
    ref?: Ref<HTMLElement>;
}
export default function Transition({ children, name, classes }: {
    children: ReactNode;
    name: string;
    classes: Record<string, string>;
}) {
    const child = Children.toArray(children).find(isValidElement) as ReactElement<ChildProps> | undefined;
    const present = child !== undefined;
    const [mounted, setMounted] = useState(present);
    const [stage, setStage] = useState('');
    const previous = useRef(present), last = useRef(child), element = useRef<HTMLElement | null>(null);
    if (child)
        last.current = child;
    useLayoutEffect(() => {
        if (previous.current === present)
            return;
        previous.current = present;
        setMounted(true);
        setStage(present ? 'enter-from' : 'leave-from');
        let frame2 = 0, timer: ReturnType<typeof setTimeout> | undefined;
        const frame1 = requestAnimationFrame(() => {
            frame2 = requestAnimationFrame(() => {
                const duration = element.current ? Math.max(...getComputedStyle(element.current).transitionDuration.split(',').map(value => value.trim().endsWith('ms') ? parseFloat(value) : parseFloat(value) * 1000), 0) : 150;
                setStage(present ? 'enter-to' : 'leave-to');
                timer = setTimeout(() => { if (!present)
                    setMounted(false); setStage(''); }, duration || 150);
            });
        });
        return () => { cancelAnimationFrame(frame1); cancelAnimationFrame(frame2); if (timer)
            clearTimeout(timer); };
    }, [present]);
    const current = child ?? last.current;
    if ((!present && !mounted) || !current)
        return null;
    const names = stage ? [name + '-' + stage, name + '-' + (stage.startsWith('enter') ? 'enter-active' : 'leave-active')] : [];
    return cloneElement(current, { className: [current.props.className, ...names.flatMap(value => [value, classes[value]])].filter(Boolean).join(' '), ref: node => {
            element.current = node;
            const ref = current.props.ref;
            if (typeof ref === 'function')
                ref(node);
            else if (ref)
                ref.current = node;
        } });
}
