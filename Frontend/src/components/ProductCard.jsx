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

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 transition hover:border-violet-500/40">

      {/* IMAGE */}
      <div className="flex h-48 items-center justify-center bg-slate-900">
        {image ? (
          <img
            src={image}
            alt={name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="text-4xl text-slate-700">
            ◇
          </div>
        )}
      </div>

      {/* CONTENT */}
      <div className="p-4">

        <div className="mb-2">
          <p className="text-xs text-slate-500">
            {category}
          </p>

          <h3 className="mt-1 font-medium text-white">
            {name}
          </h3>
        </div>

        {/* PRICE */}
        <div className="mb-4 flex items-end justify-between">

          <div>
            <p className="text-xs text-slate-500">
              Price
            </p>

            <p className="text-xl font-semibold text-white">
              ₹{price.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </div>

          <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-[10px] text-emerald-400">
            Available
          </span>

        </div>

        {/* ACTIONS */}
        <div className="grid grid-cols-2 gap-2">

          <button
            onClick={() =>
              onAction(
                "select_product",
                product,
                data
              )
            }
            className="rounded-xl border border-slate-700 px-3 py-2.5 text-xs font-medium text-slate-300 transition hover:bg-slate-800"
          >
            View Product
          </button>

          <button
            onClick={() =>
              onAction(
                "negotiate",
                product,
                data
              )
            }
            className="rounded-xl bg-violet-600 px-3 py-2.5 text-xs font-medium text-white transition hover:bg-violet-500"
          >
            Negotiate
          </button>

        </div>

      </div>
    </div>
  );
}

export default ProductCard;