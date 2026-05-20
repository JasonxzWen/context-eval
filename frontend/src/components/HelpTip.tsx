type HelpTipProps = {
  text: string;
};

export function HelpTip({ text }: HelpTipProps) {
  return (
    <span className="help-tip" aria-hidden="true" title={text}>
      ?
    </span>
  );
}
