import { useState } from "react";

function ProductCard({
  product,
  data,
  onAction,
}) {
  const productId =
    product.product_id ||
    product.id;

  const name =
    product.name ||
    product.product_name ||
    `Product ${productId}`;

  const category =
    product.category ||
    product.category_name ||
    "Product";

  const price = Number(
    product.price ||
    product.final_price ||
    product.unit_price ||
    0
  );

  const image =
    product.image_url ||
    product.image ||
    product.thumbnail;

  const [quantity, setQuantity] = useState(
    Math.min(10, Math.max(1, Number(product.quantity || 1)))
  );

  return (
    <div className="overflow-hidden rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] transition-all duration-300 hover:border-[#d9a353] hover:shadow-lg">

      {/* IMAGE */}
      <div className="flex h-48 items-center justify-center bg-[#0e0b08]">
        {image ? (
          <img
            src={image}
            alt={name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="text-4xl text-[rgba(240,231,214,0.16)]">
            ◇
          </div>
        )}
      </div>

      {/* CONTENT */}
      <div className="p-4">

        <div className="mb-2">
          <p className="text-xs text-[rgba(240,231,214,0.45)]">
            Category {category}
          </p>

          <h3 className="mt-1 font-medium text-[#f0e7d6]">
            {name}
          </h3>
        </div>

        {/* PRICE */}
        <div className="mb-4 flex items-end justify-between">

          <div>
            <p className="text-xs text-[rgba(240,231,214,0.45)]">
              Price
            </p>

            <p className="text-xl font-semibold text-[#f0e7d6]">
              ₹{price.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </div>

          <span className="rounded-full bg-[rgba(217,163,83,0.15)] px-2 py-1 text-[10px] text-[#d9a353]">
            Available
          </span>

        </div>

        {/* QUANTITY */}
        <div className="mb-4 flex items-center justify-between rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] px-3 py-2">
          <span className="text-xs text-[rgba(240,231,214,0.45)]">Quantity</span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled={quantity <= 1}
              onClick={() => setQuantity((value) => Math.max(1, value - 1))}
              className="flex h-7 w-7 items-center justify-center rounded-lg border border-[rgba(240,231,214,0.16)] text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353] disabled:cursor-not-allowed disabled:opacity-40"
            >
              -
            </button>
            <span className="min-w-[20px] text-center text-sm font-medium text-[#f0e7d6]">
              {quantity}
            </span>
            <button
              type="button"
              disabled={quantity >= 10}
              onClick={() => setQuantity((value) => Math.min(10, value + 1))}
              className="flex h-7 w-7 items-center justify-center rounded-lg border border-[rgba(240,231,214,0.16)] text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353] disabled:cursor-not-allowed disabled:opacity-40"
            >
              +
            </button>
          </div>
        </div>

        {/* ACTIONS */}
        <div className="grid grid-cols-2 gap-2">

          <button
            onClick={() =>
              onAction(
                "select_product",
                { ...product, quantity },
                data
              )
            }
            className="rounded-lg border border-[rgba(240,231,214,0.16)] px-3 py-2.5 text-xs font-medium text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353]"
          >
            View Product
          </button>

          <button
            onClick={() =>
              onAction(
                "negotiate",
                { ...product, quantity },
                data
              )
            }
            className="rounded-lg bg-[#d9a353] px-3 py-2.5 text-xs font-medium text-[#0e0b08] transition-all duration-300 hover:bg-[#f0e7d6]"
          >
            Negotiate
          </button>

        </div>

      </div>
    </div>
  );
}

export default ProductCard;