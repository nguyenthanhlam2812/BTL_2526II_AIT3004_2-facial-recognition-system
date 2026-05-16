type ScanFrameProps = {
  active: boolean;
  state: "idle" | "scanning" | "success" | "fail";
};

export default function ScanFrame({ active, state }: ScanFrameProps) {
  const className = `scan-frame ${active ? state : "idle"}`;

  return (
    <div className={className} aria-hidden="true">
      <span className="scan-corner tl" />
      <span className="scan-corner tr" />
      <span className="scan-corner bl" />
      <span className="scan-corner br" />
      {active && <span className="scan-line" />}
    </div>
  );
}
