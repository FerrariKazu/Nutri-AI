const StarBorder = ({
  as: Component = 'button',
  className = '',
  color = 'rgb(251, 146, 60)',
  speed = '4s',
  thickness = 4,
  children,
  ...rest
}) => {
  return (
    <Component
      className={`relative inline-block overflow-hidden rounded-[20px] ${className}`}
      style={{
        padding: `${thickness}px`,
        background: 'linear-gradient(135deg, rgba(251, 146, 60, 0.2), rgba(249, 115, 22, 0.3))',
        ...rest.style
      }}
      {...rest}
    >
      <div
        className="absolute w-[500%] h-[100%] bottom-[-30px] right-[-400%] rounded-full animate-star-movement-bottom"
        style={{
          background: `radial-gradient(circle, ${color} 0%, ${color}EE 10%, ${color}88 20%, transparent 35%)`,
          animationDuration: speed,
          opacity: 1,
        }}
      ></div>
      <div
        className="absolute w-[500%] h-[100%] top-[-30px] left-[-400%] rounded-full animate-star-movement-top"
        style={{
          background: `radial-gradient(circle, ${color} 0%, ${color}EE 10%, ${color}88 20%, transparent 35%)`,
          animationDuration: speed,
          opacity: 1,
        }}
      ></div>
      <div className="relative bg-gradient-to-b from-black to-gray-900 border border-gray-800 text-white text-center text-[16px] py-[16px] px-[26px] rounded-[18px]">
        {children}
      </div>
    </Component>
  );
};

export default StarBorder;