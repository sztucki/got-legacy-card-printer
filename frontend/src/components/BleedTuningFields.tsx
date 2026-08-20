interface BleedTuningFieldsProps {
  sdStrength: number;
  onSdStrengthChange: (value: number) => void;
  sdMaskBlur: number;
  onSdMaskBlurChange: (value: number) => void;
  seedText: string;
  onSeedTextChange: (value: string) => void;
  removeFooterText: boolean;
  onRemoveFooterTextChange: (value: boolean) => void;
  footerHeightPercent: number;
  onFooterHeightPercentChange: (value: number) => void;
  disabled: boolean;
}

export function BleedTuningFields({
  sdStrength,
  onSdStrengthChange,
  sdMaskBlur,
  onSdMaskBlurChange,
  seedText,
  onSeedTextChange,
  removeFooterText,
  onRemoveFooterTextChange,
  footerHeightPercent,
  onFooterHeightPercentChange,
  disabled,
}: BleedTuningFieldsProps) {
  return (
    <>
      <label style={{ marginLeft: "1rem" }}>
        Strength:{" "}
        <input
          type="number"
          min={0}
          max={1}
          step={0.05}
          value={sdStrength}
          disabled={disabled}
          onChange={(event) => onSdStrengthChange(Number(event.target.value))}
          style={{ width: "4rem" }}
        />
      </label>
      <label style={{ marginLeft: "1rem" }}>
        Mask blur:{" "}
        <input
          type="number"
          min={0}
          step={1}
          value={sdMaskBlur}
          disabled={disabled}
          onChange={(event) => onSdMaskBlurChange(Number(event.target.value))}
          style={{ width: "4rem" }}
        />
      </label>
      <label style={{ marginLeft: "1rem" }}>
        Seed (blank = random):{" "}
        <input
          type="number"
          value={seedText}
          disabled={disabled}
          onChange={(event) => onSeedTextChange(event.target.value)}
          style={{ width: "6rem" }}
        />
      </label>
      <label style={{ marginLeft: "1rem" }}>
        <input
          type="checkbox"
          checked={removeFooterText}
          disabled={disabled}
          onChange={(event) => onRemoveFooterTextChange(event.target.checked)}
        />{" "}
        Remove blurry footer text
      </label>
      {removeFooterText && (
        <label style={{ marginLeft: "1rem" }}>
          Footer height:{" "}
          <input
            type="number"
            min={1}
            max={30}
            step={0.1}
            value={footerHeightPercent}
            disabled={disabled}
            onChange={(event) => onFooterHeightPercentChange(Number(event.target.value))}
            style={{ width: "4rem" }}
          />
          %
        </label>
      )}
    </>
  );
}
