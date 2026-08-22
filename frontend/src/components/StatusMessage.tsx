type Props = {
  tone: "info" | "success" | "error";
  children: React.ReactNode;
};

export function StatusMessage({ tone, children }: Props) {
  return (
    <div className={`status status--${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}
