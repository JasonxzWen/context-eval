type HelpTipProps = {
  text: string;
};

export function HelpTip({ text }: HelpTipProps) {
  return <small className="inline-help">{text}</small>;
}
