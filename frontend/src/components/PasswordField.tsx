import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import { IconButton, InputAdornment, TextField, type TextFieldProps } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";

type Props = TextFieldProps & {
  /** controlled mode: lets two fields (password + repeat) share one "eye" state */
  visible?: boolean;
  onVisibleChange?: (visible: boolean) => void;
};

/** Password input with a show/hide toggle ("eye"). */
export default function PasswordField({ visible, onVisibleChange, ...props }: Props) {
  const { t } = useTranslation();
  const [own, setOwn] = useState(false);
  const shown = visible ?? own;
  const toggle = () => (onVisibleChange ? onVisibleChange(!shown) : setOwn(!shown));
  return (
    <TextField
      {...props}
      type={shown ? "text" : "password"}
      slotProps={{
        ...props.slotProps,
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                edge="end"
                aria-label={shown ? t("common.hidePassword") : t("common.showPassword")}
                onClick={toggle}
                onMouseDown={(e) => e.preventDefault()} // keep focus in the field
              >
                {shown ? <VisibilityOff /> : <Visibility />}
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
    />
  );
}
