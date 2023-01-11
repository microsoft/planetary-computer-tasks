import { Icon, Stack, Text } from "@fluentui/react";
import React from "react";
import { gapRegular } from "styles/global";

interface IconLabelProps {
  iconName: string;
  label: string | undefined;
  className?: string;
}

export const IconLabel: React.FC<IconLabelProps> = ({
  iconName,
  label,
  className,
}) => {
  return (
    <Stack
      className={className}
      horizontal
      verticalAlign="center"
      tokens={gapRegular}
    >
      <Icon iconName={iconName} />
      <Text variant="mediumPlus">{label}</Text>
    </Stack>
  );
};
