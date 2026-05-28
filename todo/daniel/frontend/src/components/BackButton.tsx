import { useNavigate } from "react-router-dom";

interface Props {
  fallback?: string;
  className?: string;
}

export default function BackButton({ fallback = "/", className = "" }: Props) {
  const navigate = useNavigate();
  const onClick = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(fallback);
    }
  };
  return (
    <button
      onClick={onClick}
      className={
        "inline-flex items-center gap-1 px-2.5 py-1 text-xs text-gray-400 hover:text-gray-100 " +
        "bg-gray-800/60 hover:bg-gray-700 border border-gray-700 rounded transition " +
        className
      }
      title="回到上一頁"
    >
      ← 返回
    </button>
  );
}
