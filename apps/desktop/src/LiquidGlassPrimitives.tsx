import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react';

type GlassTone = 'default' | 'strong' | 'subtle';
type GlassButtonVariant = 'default' | 'primary' | 'ghost' | 'danger';
type GlassPillTone = 'default' | 'success' | 'warning' | 'danger';

function classNames(values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ');
}

export interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  variant?: GlassButtonVariant;
}

export function GlassButton({
  children,
  className,
  icon,
  type = 'button',
  variant = 'default',
  ...props
}: GlassButtonProps) {
  return (
    <button
      {...props}
      type={type}
      className={classNames(['biotGlassButton', `is-${variant}`, className])}
    >
      {icon ? <span className="biotGlassButtonIcon">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
}
export interface GlassPanelProps extends Omit<HTMLAttributes<HTMLElement>, 'title'> {
  children: ReactNode;
  description?: ReactNode;
  flow?: boolean;
  title?: string;
  tone?: GlassTone;
}

export function GlassPanel({
  children,
  className,
  description,
  flow = false,
  title,
  tone = 'default',
  ...props
}: GlassPanelProps) {
  return (
    <section
      {...props}
      aria-label={title || props['aria-label']}
      className={classNames(['biotGlassPanel', `is-${tone}`, flow && 'biotLiquidBorder', className])}
      role={title ? 'region' : props.role}
    >
      {title || description ? (
        <header className="biotGlassPanelHeader">
          {title ? <strong>{title}</strong> : null}
          {description ? <span>{description}</span> : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}

export interface GlassPillProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  icon?: ReactNode;
  tone?: GlassPillTone;
}

export function GlassPill({
  children,
  className,
  icon,
  tone = 'default',
  ...props
}: GlassPillProps) {
  return (
    <span {...props} className={classNames(['biotGlassPill', `is-${tone}`, className])}>
      {icon ? <span className="biotGlassPillIcon">{icon}</span> : null}
      {children}
    </span>
  );
}

export interface GlassToolbarProps extends HTMLAttributes<HTMLDivElement> {
  ariaLabel: string;
  children: ReactNode;
}

export function GlassToolbar({
  ariaLabel,
  children,
  className,
  ...props
}: GlassToolbarProps) {
  return (
    <div {...props} aria-label={ariaLabel} className={classNames(['biotGlassToolbar', className])}>
      {children}
    </div>
  );
}
